package com.clinevo.smart.inbox.backend.service;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.util.Map;

import tools.jackson.databind.json.JsonMapper;

@Service
public class DocumentService {

    private final HttpClient httpClient;
    private final JsonMapper jsonMapper;

    @Value("${ai.service.url:http://127.0.0.1:8002}")
    private String aiServiceUrl;

    @org.springframework.beans.factory.annotation.Autowired
    public DocumentService(
            @Value("${ai.service.url:http://127.0.0.1:8002}") String aiServiceUrl) {
        this.aiServiceUrl = aiServiceUrl;
        this.httpClient = HttpClient.newBuilder()
                .version(HttpClient.Version.HTTP_1_1)
                .build();
        this.jsonMapper = JsonMapper.builder().build();
    }

    DocumentService(HttpClient httpClient, JsonMapper jsonMapper) {
        this.aiServiceUrl = "http://127.0.0.1:8002";
        this.httpClient = httpClient;
        this.jsonMapper = jsonMapper;
    }

    public Map<String, Object> analyzeDocument(MultipartFile file) {
        try {
            String boundary = "----ClinevoBoundary" + System.currentTimeMillis();

            byte[] fileBytes = file.getBytes();

            String prefix =
                    "--" + boundary + "\r\n" +
                    "Content-Disposition: form-data; name=\"file\"; filename=\"" +
                    file.getOriginalFilename() + "\"\r\n" +
                    "Content-Type: application/pdf\r\n\r\n";

            String suffix = "\r\n--" + boundary + "--\r\n";

            byte[] prefixBytes = prefix.getBytes(StandardCharsets.UTF_8);
            byte[] suffixBytes = suffix.getBytes(StandardCharsets.UTF_8);

            byte[] body = new byte[
                    prefixBytes.length + fileBytes.length + suffixBytes.length
            ];

            System.arraycopy(prefixBytes, 0, body, 0, prefixBytes.length);
            System.arraycopy(
                    fileBytes,
                    0,
                    body,
                    prefixBytes.length,
                    fileBytes.length
            );
            System.arraycopy(
                    suffixBytes,
                    0,
                    body,
                    prefixBytes.length + fileBytes.length,
                    suffixBytes.length
            );

            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(aiServiceUrl.replaceAll("/$", "")
                            + "/analyze-document"))
                    .header(
                            "Content-Type",
                            "multipart/form-data; boundary=" + boundary
                    )
                    .header("Accept", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofByteArray(body))
                    .build();

            HttpResponse<String> response = httpClient.send(
                    request,
                    HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8)
            );

            if (response.statusCode() < 200 || response.statusCode() >= 300) {
                throw new RuntimeException(
                        "AI document service returned HTTP "
                                + response.statusCode()
                                + ": "
                                + response.body()
                );
            }

            return jsonMapper.readValue(response.body(), Map.class);

        } catch (Exception e) {
            throw new RuntimeException(
                    "Document analysis failed: " + e.getMessage(),
                    e
            );
        }
    }
}
