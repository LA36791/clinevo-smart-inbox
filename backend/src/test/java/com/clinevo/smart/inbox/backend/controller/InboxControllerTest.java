package com.clinevo.smart.inbox.backend.controller;

import com.clinevo.smart.inbox.backend.service.AiService;
import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class InboxControllerTest {

    @Test
    void analyzeDelegatesToAiService() {
        AiService aiService = mock(AiService.class);
        InboxController controller = new InboxController(aiService);

        Map<String, Object> request = Map.of("documentId", "abc123", "content", "hello");
        Map<String, Object> expected = Map.of("status", "ok", "documentId", "abc123");

        when(aiService.analyze(request)).thenReturn(expected);

        assertEquals(expected, controller.analyze(request));
    }

    @Test
    void healthReturnsServiceStatus() {
        InboxController controller = new InboxController(mock(AiService.class));

        assertEquals(
                Map.of("status", "ok", "service", "smart-inbox-backend"),
                controller.health()
        );
    }
}
