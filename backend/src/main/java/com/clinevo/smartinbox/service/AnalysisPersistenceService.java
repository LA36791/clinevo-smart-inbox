package com.clinevo.smartinbox.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;
import org.springframework.stereotype.Service;

import java.sql.PreparedStatement;

@Service
public class AnalysisPersistenceService {

private final JdbcTemplate jdbc;
private final ObjectMapper mapper = new ObjectMapper();

public AnalysisPersistenceService(JdbcTemplate jdbc) {
    this.jdbc = jdbc;
}

public Long persist(String filename, Object result, long processingTimeMs) throws Exception {

    JsonNode root = mapper.valueToTree(result);

    String documentType = text(root, "document_type");
    String summary = text(root, "summary");
    boolean humanReview = root.path("human_review_required").asBoolean(true);

    Long documentId = insertAndGetId(
        "INSERT INTO DOCUMENT (FILE_NAME, DOCUMENT_TYPE, ORIGINAL_LINK) VALUES (?, ?, ?)",
        filename,
        documentType,
        filename
    );

    Long analysisId = insertAndGetId(
        "INSERT INTO ANALYSIS_RESULT " +
        "(DOCUMENT_ID, SUMMARY, HUMAN_REVIEW_REQUIRED, PROCESSING_TIME_MS) " +
        "VALUES (?, ?, ?, ?)",
        documentId,
        summary,
        humanReview,
        processingTimeMs
    );

    if (root.has("categories") && root.get("categories").isArray()) {

        for (JsonNode category : root.get("categories")) {

            jdbc.update(
                "INSERT INTO CLASSIFICATION " +
                "(ANALYSIS_ID, CATEGORY, CONFIDENCE, REASON) " +
                "VALUES (?, ?, ?, ?)",
                analysisId,
                text(category, "category"),
                category.path("confidence").asDouble(0),
                text(category, "reason")
            );
        }
    }

    if (root.has("facts") && root.get("facts").isArray()) {

        for (JsonNode fact : root.get("facts")) {

            Long factId = insertAndGetId(
                "INSERT INTO EXTRACTED_FACT " +
                "(ANALYSIS_ID, FIELD_NAME, VALUE_TEXT, CONFIDENCE) " +
                "VALUES (?, ?, ?, ?)",
                analysisId,
                text(fact, "field"),
                text(fact, "value"),
                fact.path("confidence").asDouble(0)
            );

            if (fact.has("evidence") && fact.get("evidence").isArray()) {

                for (JsonNode evidence : fact.get("evidence")) {

                    Integer page = evidence.path("page").isNull()
                        ? null
                        : evidence.path("page").asInt();

                    jdbc.update(
                        "INSERT INTO EVIDENCE " +
                        "(FACT_ID, SOURCE_TYPE, SOURCE_ID, PAGE_NUMBER, " +
                        "EVIDENCE_TEXT, CONFIDENCE) " +
                        "VALUES (?, ?, ?, ?, ?, ?)",
                        factId,
                        text(evidence, "source_type"),
                        text(evidence, "source_id"),
                        page,
                        text(evidence, "text"),
                        evidence.path("confidence").asDouble(0)
                    );
                }
            }
        }
    }

    jdbc.update(
        "INSERT INTO PROCESSING_LOG " +
        "(DOCUMENT_ID, STAGE, PROCESSING_TIME_MS, STATUS) " +
        "VALUES (?, ?, ?, ?)",
        documentId,
        "AI_ANALYSIS",
        processingTimeMs,
        "COMPLETED"
    );

    return analysisId;
}

private Long insertAndGetId(String sql, Object... params) {

    KeyHolder keyHolder = new GeneratedKeyHolder();

    jdbc.update(connection -> {

        PreparedStatement ps =
            connection.prepareStatement(
                sql,
                new String[]{"ID"}
            );

        for (int i = 0; i < params.length; i++) {
            ps.setObject(i + 1, params[i]);
        }

        return ps;

    }, keyHolder);

    Number key;

    // H2 may return multiple generated keys; getKey() then throws.
    // Read the ID column directly from the returned key map instead.
    if (keyHolder.getKeys() != null && keyHolder.getKeys().containsKey("ID")) {
        key = (Number) keyHolder.getKeys().get("ID");
    } else {
        key = keyHolder.getKey();
    }

    if (key == null) {
        throw new IllegalStateException(
            "Database did not return a generated ID for: " + sql
        );
    }

    return key.longValue();
}

private String text(JsonNode node, String field) {

    JsonNode value = node.get(field);

    if (value == null || value.isNull()) {
        return "Not stated";
    }

    if (value.isTextual()) {
        return value.asText();
    }

    return value.toString();
}

}
