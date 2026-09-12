package com.clinevo.smart.inbox.backend.service;

import org.junit.jupiter.api.Test;
import tools.jackson.databind.json.JsonMapper;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class AiServiceTest {

    @Test
    void analyzeReturnsParsedResponseFromAiService() throws Exception {
        HttpClient httpClient = mock(HttpClient.class);
        JsonMapper jsonMapper = JsonMapper.builder().build();
        AiService service = new AiService(httpClient, jsonMapper);

        @SuppressWarnings("unchecked")
        HttpResponse<String> response = mock(HttpResponse.class);
        when(response.statusCode()).thenReturn(200);
        when(response.body()).thenReturn("{\"summary\":\"ok\",\"documentId\":\"abc123\"}");
        when(httpClient.send(any(HttpRequest.class), any(HttpResponse.BodyHandler.class))).thenReturn(response);

        Map<String, Object> request = Map.of("documentId", "abc123", "content", "hello");
        Map<String, Object> result = service.analyze(request);

        assertEquals("ok", result.get("summary"));
        assertEquals("abc123", result.get("documentId"));
    }

    @Test
    void analyzeThrowsWhenAiServiceReturnsFailureStatus() throws Exception {
        HttpClient httpClient = mock(HttpClient.class);
        JsonMapper jsonMapper = JsonMapper.builder().build();
        AiService service = new AiService(httpClient, jsonMapper);

        @SuppressWarnings("unchecked")
        HttpResponse<String> response = mock(HttpResponse.class);
        when(response.statusCode()).thenReturn(500);
        when(response.body()).thenReturn("Server down");
        when(httpClient.send(any(HttpRequest.class), any(HttpResponse.BodyHandler.class))).thenReturn(response);

        RuntimeException exception = assertThrows(
                RuntimeException.class,
                () -> service.analyze(Map.of("documentId", "bad"))
        );

        assertTrue(exception.getMessage().contains("AI service returned HTTP 500"));
    }
}
