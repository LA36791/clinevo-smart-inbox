package com.clinevo.smart.inbox.backend.service;

import org.springframework.stereotype.Service;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.util.Map;

import tools.jackson.databind.json.JsonMapper;

@Service
public class AiService {

    private final HttpClient httpClient;
    private final JsonMapper jsonMapper;

    public AiService() {
        this(
                HttpClient.newBuilder()
                        .version(HttpClient.Version.HTTP_1_1)
                        .build(),
                JsonMapper.builder().build()
        );
    }

    AiService(HttpClient httpClient, JsonMapper jsonMapper) {
        this.httpClient = httpClient;
        this.jsonMapper = jsonMapper;
    }

    public Map<String, Object> analyze(Map<String, Object> request) {
        try {
            String json = jsonMapper.writeValueAsString(request);

            System.out.println("Sending JSON to AI service: " + json);

            HttpRequest httpRequest = HttpRequest.newBuilder()
                    .uri(URI.create("http://127.0.0.1:8000/analyze"))
                    .header("Content-Type", "application/json")
                    .header("Accept", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString(json, StandardCharsets.UTF_8))
                    .build();

            HttpResponse<String> response = httpClient.send(
                    httpRequest,
                    HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8)
            );

            System.out.println("AI service HTTP status: " + response.statusCode());
            System.out.println("AI service response: " + response.body());

            if (response.statusCode() < 200 || response.statusCode() >= 300) {
                throw new RuntimeException(
                        "AI service returned HTTP "
                                + response.statusCode()
                                + ": "
                                + response.body()
                );
            }

            return jsonMapper.readValue(response.body(), Map.class);

        } catch (Exception e) {
            throw new RuntimeException(
                    "AI service request failed: " + e.getMessage(), e
            );
        }
    }
}
