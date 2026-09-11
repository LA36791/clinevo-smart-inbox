package com.clinevo.smartinbox.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestTemplate;

@Service
public class AiService {

    @Value("${ai.service.url}")
    private String aiUrl;

    private final RestTemplate restTemplate = new RestTemplate();
    private final AnalysisPersistenceService persistenceService;
    private final ObjectMapper mapper = new ObjectMapper();

    public AiService(AnalysisPersistenceService persistenceService) {
        this.persistenceService = persistenceService;
    }

    public Object analyze(byte[] file, String filename) throws Exception {

        long start = System.currentTimeMillis();

        ByteArrayResource resource = new ByteArrayResource(file) {
            @Override
            public String getFilename() {
                return filename;
            }
        };

        MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
        body.add("file", resource);

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.MULTIPART_FORM_DATA);
        headers.setAccept(java.util.List.of(MediaType.APPLICATION_JSON));

        HttpEntity<MultiValueMap<String, Object>> request =
                new HttpEntity<>(body, headers);

        ResponseEntity<JsonNode> response = restTemplate.postForEntity(
                aiUrl + "/analyze-document",
                request,
                JsonNode.class
        );

        long processingTime = System.currentTimeMillis() - start;

        JsonNode result = response.getBody();

        if (result == null) {
            throw new IllegalStateException("AI service returned an empty response");
        }

        Long analysisId =
                persistenceService.persist(filename, result, processingTime);

        ObjectNode enrichedResult;

        if (result.isObject()) {
            enrichedResult = (ObjectNode) result.deepCopy();
        } else {
            enrichedResult = mapper.createObjectNode();
            enrichedResult.set("result", result);
        }

        enrichedResult.put("analysisId", analysisId);
        enrichedResult.put("backendProcessingTimeMs", processingTime);

        return enrichedResult;
    }
}
