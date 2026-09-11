package com.clinevo.smartinbox.controller;

import com.clinevo.smartinbox.model.ReviewAction;
import com.clinevo.smartinbox.repository.ReviewActionRepository;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.Map;

@RestController
@RequestMapping("/api/review")
@CrossOrigin(origins = "*")
public class ReviewController {

    private final ReviewActionRepository repository;

    public ReviewController(ReviewActionRepository repository) {
        this.repository = repository;
    }

    @PostMapping
    public ResponseEntity<?> review(@RequestBody Map<String, Object> body) {

        System.out.println("=== REVIEW REQUEST RECEIVED ===");
        System.out.println("BODY: " + body);

        try {
            ReviewAction action = new ReviewAction();

            Object analysisId = body.get("analysisId");
            if (analysisId != null) {
                action.setAnalysisId(Long.parseLong(analysisId.toString()));
            }

            action.setAction(String.valueOf(body.getOrDefault("action", "")));
            action.setOriginalCategory(
                String.valueOf(body.getOrDefault("originalCategory", ""))
            );
            action.setFinalCategory(
                String.valueOf(body.getOrDefault("finalCategory", ""))
            );
            action.setReviewer(
                String.valueOf(body.getOrDefault("reviewer", ""))
            );
            action.setNotes(
                String.valueOf(body.getOrDefault("notes", ""))
            );
            action.setActionTimestamp(LocalDateTime.now());

            ReviewAction saved = repository.save(action);

            System.out.println("=== REVIEW SAVED: ID=" + saved.getId() + " ===");

            return ResponseEntity.ok(saved);

        } catch (Exception e) {

            e.printStackTrace();

            return ResponseEntity.badRequest().body(
                Map.of(
                    "error", "Review save failed",
                    "exception", e.getClass().getName(),
                    "message", String.valueOf(e.getMessage())
                )
            );
        }
    }

    @GetMapping
    public Object history() {
        return repository.findAll();
    }
}