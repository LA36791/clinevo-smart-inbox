package com.clinevo.smartinbox;

import com.clinevo.smartinbox.model.ReviewAction;
import com.clinevo.smartinbox.repository.ReviewActionRepository;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.web.client.RestTemplate;

import java.util.ArrayList;
import java.util.List;

import static org.mockito.ArgumentMatchers.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.multipart;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

/**
 * Backend test suite (no live AI service required: RestTemplate is mocked).
 * Covers health, analyze, review accept/override/invalid, audit, batch overflow
 * (SKIPPED) and failure isolation, per release hardening phase 9.
 */
@SpringBootTest
@AutoConfigureMockMvc
@TestPropertySource(properties = {
        "spring.datasource.url=jdbc:h2:mem:testdb;MODE=LEGACY;DB_CLOSE_DELAY=-1",
        "spring.jpa.hibernate.ddl-auto=create-drop",
        "ai.service.url=http://localhost:19999"
})
class BackendApiTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ReviewActionRepository reviewRepository;

    @MockBean
    private RestTemplate restTemplate;

    private static final String AI_RESPONSE = """
            {
              "categories": [
                {"category": "SAFETY_REPORT_ICSR", "confidence": 0.91, "reason": "adverse event indicators"}
              ],
              "facts": [
                {"field": "patient_age", "value": "54", "confidence": 0.9,
                 "evidence": [{"page": 1, "text": "Patient age: 54", "confidence": 0.95}]},
                {"field": "product", "value": "CardioRelax", "confidence": 0.88, "evidence": []}
              ],
              "human_review_required": false,
              "processing_time_ms": 12
            }
            """;

    @BeforeEach
    void resetRepo() {
        reviewRepository.deleteAll();
    }

    private void mockAi() throws Exception {
        ObjectMapper mapper = new ObjectMapper();
        JsonNode node = mapper.readTree(AI_RESPONSE);
        Mockito.when(restTemplate.postForEntity(anyString(), any(HttpEntity.class), eq(JsonNode.class)))
                .thenReturn(new ResponseEntity<>(node, HttpStatus.OK));
    }

    private MockMultipartFile pdf(String name) {
        return new MockMultipartFile("files", name, "application/pdf",
                "%PDF-1.4 fake".getBytes());
    }

    @Test
    void healthIsUp() throws Exception {
        mockMvc.perform(get("/api/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("UP"));
    }

    @Test
    void analyzePersistsAndEnriches() throws Exception {
        mockAi();
        mockMvc.perform(multipart("/api/analyze").file(
                        new MockMultipartFile("file", "case.pdf", "application/pdf", "%PDF-1.4".getBytes())))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.analysisId").exists())
                .andExpect(jsonPath("$.categories[0].category").value("SAFETY_REPORT_ICSR"))
                .andExpect(jsonPath("$.backendProcessingTimeMs").exists());
    }

    @Test
    void reviewAcceptIsAudited() throws Exception {
        mockMvc.perform(post("/api/review")
                        .contentType("application/json")
                        .content("{\"analysisId\":1,\"action\":\"ACCEPT\",\"originalCategory\":\"SAFETY_REPORT_ICSR\",\"finalCategory\":\"SAFETY_REPORT_ICSR\",\"reviewer\":\"tester\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").exists());

        mockMvc.perform(get("/api/audit?analysisId=1"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].action").value("ACCEPT"));
    }

    @Test
    void reviewOverrideIsAudited() throws Exception {
        mockMvc.perform(post("/api/review")
                        .contentType("application/json")
                        .content("{\"analysisId\":2,\"action\":\"OVERRIDE\",\"originalCategory\":\"SAFETY_REPORT_ICSR\",\"finalCategory\":\"QUALITY_COMPLAINT_PQC\",\"reviewer\":\"tester\",\"notes\":\"wrong bucket\"}"))
                .andExpect(status().isOk());

        mockMvc.perform(get("/api/audit?analysisId=2"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].action").value("OVERRIDE"))
                .andExpect(jsonPath("$[0].finalCategory").value("QUALITY_COMPLAINT_PQC"));
    }

    @Test
    void invalidReviewActionReturns400() throws Exception {
        mockMvc.perform(post("/api/review")
                        .contentType("application/json")
                        .content("{\"analysisId\":3,\"action\":\"BOGUS\"}"))
                .andExpect(status().isBadRequest());
    }

    @Test
    void batchOverflowIsSkippedNotDropped() throws Exception {
        mockAi();
        List<MockMultipartFile> files = new ArrayList<>();
        for (int i = 0; i < 17; i++) {
            files.add(pdf("doc" + i + ".pdf"));
        }
        mockMvc.perform(multipart("/api/analyze-batch").file(files.get(0)).file(files.get(1))
                        .file(files.get(2)).file(files.get(3)).file(files.get(4)).file(files.get(5))
                        .file(files.get(6)).file(files.get(7)).file(files.get(8)).file(files.get(9))
                        .file(files.get(10)).file(files.get(11)).file(files.get(12)).file(files.get(13))
                        .file(files.get(14)).file(files.get(15)).file(files.get(16)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].status").value("SKIPPED"))
                .andExpect(jsonPath("$[1].status").value("SKIPPED"))
                .andExpect(jsonPath("$[2].status").value("OK"))
                .andExpect(jsonPath("$.length()").value(17));
    }

    @Test
    void batchFailureIsolation() throws Exception {
        // first call OK, second throws -> batch must still return 2 entries
        ObjectMapper mapper = new ObjectMapper();
        JsonNode node;
        try {
            node = mapper.readTree(AI_RESPONSE);
        } catch (Exception e) {
            throw new IllegalStateException(e);
        }
        Mockito.when(restTemplate.postForEntity(anyString(), any(HttpEntity.class), eq(JsonNode.class)))
                .thenReturn(new ResponseEntity<>(node, HttpStatus.OK))
                .thenThrow(new RuntimeException("AI service down"));

        mockMvc.perform(multipart("/api/analyze-batch")
                        .file(pdf("a.pdf")).file(pdf("b.pdf")))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(2))
                .andExpect(jsonPath("$[0].status").value("OK"))
                .andExpect(jsonPath("$[1].status").value("ERROR"))
                .andExpect(jsonPath("$[1].classification").value("NOT_PROCESSED"));
    }
}
