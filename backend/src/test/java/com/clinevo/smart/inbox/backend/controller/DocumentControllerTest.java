package com.clinevo.smart.inbox.backend.controller;

import com.clinevo.smart.inbox.backend.service.DocumentService;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockMultipartFile;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class DocumentControllerTest {

    @Test
    void analyzeDocumentRejectsEmptyFile() {
        DocumentService documentService = mock(DocumentService.class);
        DocumentController controller = new DocumentController(documentService);

        MockMultipartFile emptyFile = new MockMultipartFile(
                "file",
                "empty.pdf",
                "application/pdf",
                new byte[0]
        );

        IllegalArgumentException exception = assertThrows(
                IllegalArgumentException.class,
                () -> controller.analyzeDocument(emptyFile)
        );

        assertEquals("Uploaded PDF is empty", exception.getMessage());
    }

    @Test
    void analyzeDocumentDelegatesToDocumentService() {
        DocumentService documentService = mock(DocumentService.class);
        DocumentController controller = new DocumentController(documentService);
        MockMultipartFile file = new MockMultipartFile(
                "file",
                "report.pdf",
                "application/pdf",
                "hello from pdf".getBytes()
        );
        Map<String, Object> expected = Map.of("status", "success");

        when(documentService.analyzeDocument(file)).thenReturn(expected);

        assertEquals(expected, controller.analyzeDocument(file));
    }
}
