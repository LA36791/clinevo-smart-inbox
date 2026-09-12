package com.clinevo.smart.inbox.backend.controller;

import com.clinevo.smart.inbox.backend.service.AiService;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api")
@CrossOrigin(origins = "http://localhost:4200")
public class InboxController {

    private final AiService aiService;

    public InboxController(AiService aiService) {
        this.aiService = aiService;
    }

    @PostMapping("/analyze")
    public Map<String, Object> analyze(@RequestBody Map<String, Object> request) {
        return aiService.analyze(request);
    }

    @GetMapping("/health")
    public Map<String, String> health() {
        return Map.of(
                "status", "ok",
                "service", "smart-inbox-backend"
        );
    }
}
