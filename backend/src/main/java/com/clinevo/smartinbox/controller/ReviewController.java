package com.clinevo.smartinbox.controller;

import com.clinevo.smartinbox.model.ReviewAction;
import com.clinevo.smartinbox.repository.ReviewActionRepository;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;

@RestController
@RequestMapping("/api/review")
@CrossOrigin(origins={"http://localhost:4200","http://127.0.0.1:4200"})
public class ReviewController {

    private final ReviewActionRepository repository;

    public ReviewController(ReviewActionRepository repository) {
        this.repository = repository;
    }

    @PostMapping
    public ReviewAction review(@RequestBody ReviewAction action) {
        action.setActionTimestamp(LocalDateTime.now());
        return repository.save(action);
    }

    @GetMapping
    public Object history() {
        return repository.findAll();
    }
}
