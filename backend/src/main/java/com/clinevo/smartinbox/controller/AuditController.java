package com.clinevo.smartinbox.controller;

import com.clinevo.smartinbox.repository.ReviewActionRepository;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/audit")
@CrossOrigin(origins={"http://localhost:4200","http://127.0.0.1:4200"})
public class AuditController {

    private final ReviewActionRepository repository;

    public AuditController(ReviewActionRepository repository) {
        this.repository = repository;
    }

    @GetMapping
    public Object audit(@RequestParam(value = "analysisId", required = false) Long analysisId) {
        if (analysisId != null) { return repository.findByAnalysisIdOrderByActionTimestampDesc(analysisId); } return repository.findAll();
    }
}
