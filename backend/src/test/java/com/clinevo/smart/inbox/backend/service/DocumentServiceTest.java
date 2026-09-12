package com.clinevo.smart.inbox.backend.service;

import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockMultipartFile;
import tools.jackson.databind.json.JsonMapper;

import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class DocumentServiceTest {

    @Test
    void analyzeDocumentReturnsParsedResponseFromAiService() throws Exception {
        HttpClient httpClient = mock(HttpClient.class);
        JsonMapper jsonMapper = JsonMapper.builder().build();
        DocumentService service = new DocumentService(httpClient, jsonMapper);

        @SuppressWarnings("unchecked")
        HttpResponse<String> response = mock(HttpResponse.class);
        when(response.statusCode()).thenReturn(200);
        when(response.body()).thenReturn("{\"status\":\"success\",\"summary\":\"processed\"}");
        when(httpClient.send(any(HttpRequest.class), any(HttpResponse.BodyHandler.class))).thenReturn(response);

        MockMultipartFile file = new MockMultipartFile(
                "file",
                "report.pdf",
                "application/pdf",
                "contents".getBytes(StandardCharsets.UTF_8)
        );

        Map<String, Object> result = service.analyzeDocument(file);

        assertEquals("success", result.get("status"));
        assertEquals("processed", result.get("summary"));
    }

    @Test
    void analyzeDocumentThrowsWhenAiServiceReturnsFailureStatus() throws Exception {
        HttpClient httpClient = mock(HttpClient.class);
        JsonMapper jsonMapper = JsonMapper.builder().build();
        DocumentService service = new DocumentService(httpClient, jsonMapper);

        @SuppressWarnings("unchecked")
        HttpResponse<String> response = mock(HttpResponse.class);
        when(response.statusCode()).thenReturn(503);
        when(response.body()).thenReturn("Service unavailable");
        when(httpClient.send(any(HttpRequest.class), any(HttpResponse.BodyHandler.class))).thenReturn(response);

        MockMultipartFile file = new MockMultipartFile(
                "file",
                "report.pdf",
                "application/pdf",
                "contents".getBytes(StandardCharsets.UTF_8)
        );

        RuntimeException exception = assertThrows(
                RuntimeException.class,
                () -> service.analyzeDocument(file)
        );

        assertTrue(exception.getMessage().contains("AI document service returned HTTP 503"));
    }
}
