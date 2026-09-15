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

    private final RestTemplate restTemplate;
    private final AnalysisPersistenceService persistenceService;
    private final ObjectMapper mapper = new ObjectMapper();

    public AiService(AnalysisPersistenceService persistenceService, RestTemplate restTemplate) {
        this.persistenceService = persistenceService;
        this.restTemplate = restTemplate;
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

    /*
     * Sequential batch: reuses the single-document flow so per-document
     * traceability and persistence are identical. One failing document
     * does not abort the batch.
     */
    public java.util.List<Object> analyzeBatch(java.util.List<org.springframework.web.multipart.MultipartFile> files)
            throws Exception {

        java.util.List<Object> results = new java.util.ArrayList<>();

        if (files == null || files.isEmpty()) {
            return results;
        }

        // Cap protects the AI service from oversized batches; 15 is the
        // largest assignment batch. Overflow files are reported, not dropped.
        int limit = Math.min(files.size(), 15);
        for (int i = limit; i < files.size(); i++) {
            org.springframework.web.multipart.MultipartFile skipped = files.get(i);
            String skippedName = skipped == null ? "unknown" : skipped.getOriginalFilename();
            results.add(mapper.createObjectNode()
                    .put("file", skippedName == null ? "unknown" : skippedName)
                    .put("filename", skippedName == null ? "unknown" : skippedName)
                    .put("status", "SKIPPED")
                    .put("classification", "NOT_PROCESSED")
                    .put("confidence", 0.0)
                    .put("processingTimeMs", 0)
                    .put("humanReviewRequired", true)
                    .put("message", "Batch limit is 15 documents; file beyond the cap was not processed"));
        }

        for (int i = 0; i < limit; i++) {
            org.springframework.web.multipart.MultipartFile file = files.get(i);
            String filename =
                    file == null ? null : file.getOriginalFilename();

            if (file == null || file.isEmpty()) {
                results.add(mapper.createObjectNode()
                        .put("file", filename == null ? "unknown" : filename)
                        .put("filename", filename == null ? "unknown" : filename)
                        .put("status", "ERROR")
                        .put("classification", "NOT_PROCESSED")
                        .put("confidence", 0.0)
                        .put("processingTimeMs", 0)
                        .put("humanReviewRequired", true)
                        .put("message", "Empty file; skipped without aborting batch"));
                continue;
            }

            long docStart = System.currentTimeMillis();
            try {
                Object ok = analyze(file.getBytes(), filename);
                if (ok instanceof com.fasterxml.jackson.databind.node.ObjectNode node) {
                    node.put("file", filename == null ? "unknown" : filename);
                    node.put("filename", filename == null ? "unknown" : filename);
                    node.put("status", "OK");
                    // Flatten the most useful per-document fields for batch UI.
                    try {
                        com.fasterxml.jackson.databind.JsonNode cats = node.get("categories");
                        if (cats != null && cats.isArray() && cats.size() > 0) {
                            node.put("classification", cats.get(0).path("category").asText("UNKNOWN"));
                            node.put("confidence", cats.get(0).path("confidence").asDouble(0));
                        } else {
                            node.put("classification", "UNKNOWN");
                            node.put("confidence", 0.0);
                        }
                        node.put("humanReviewRequired", node.path("human_review_required").asBoolean(true));
                        node.put("processingTimeMs", node.path("processing_time_ms").asLong(System.currentTimeMillis() - docStart));
                        // Key extracted info: compact field->value map.
                        com.fasterxml.jackson.databind.node.ObjectNode key = mapper.createObjectNode();
                        com.fasterxml.jackson.databind.JsonNode facts = node.get("facts");
                        if (facts != null && facts.isArray()) {
                            for (com.fasterxml.jackson.databind.JsonNode f : facts) {
                                String field = f.path("field").asText("");
                                String value = f.path("value").asText("");
                                if (!field.isEmpty() && !value.isEmpty() && !"Not stated".equals(value)) {
                                    key.put(field, value);
                                }
                            }
                        }
                        node.set("keyFacts", key);
                    } catch (Exception ignored) {
                    }
                }
                results.add(ok);
            } catch (Exception e) {
                results.add(mapper.createObjectNode()
                        .put("file", filename == null ? "unknown" : filename)
                        .put("filename", filename == null ? "unknown" : filename)
                        .put("status", "ERROR")
                        .put("classification", "NOT_PROCESSED")
                        .put("confidence", 0.0)
                        .put("processingTimeMs", System.currentTimeMillis() - docStart)
                        .put("humanReviewRequired", true)
                        .put("message", e.getMessage() == null
                                ? "Analysis failed" : e.getMessage()));
            }
        }

        return results;
    }
}
