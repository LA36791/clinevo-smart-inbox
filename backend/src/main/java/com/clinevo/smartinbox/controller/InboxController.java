package com.clinevo.smartinbox.controller;

import com.clinevo.smartinbox.model.EmailMessage;
import com.clinevo.smartinbox.repository.EmailMessageRepository;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;

@RestController
@RequestMapping("/api/inbox")
@CrossOrigin(origins={"http://localhost:4200","http://127.0.0.1:4200"})
public class InboxController {

    private final EmailMessageRepository repository;

    public InboxController(EmailMessageRepository repository) {
        this.repository = repository;
    }

    @GetMapping
    public Object getInbox() {
        return repository.findAll();
    }

    @PostMapping
    public EmailMessage create(@RequestBody EmailMessage email) {
        if(email.getReceivedAt()==null)
            email.setReceivedAt(LocalDateTime.now());
        if(email.getStatus()==null)
            email.setStatus("UNPROCESSED");
        return repository.save(email);
    }
}
