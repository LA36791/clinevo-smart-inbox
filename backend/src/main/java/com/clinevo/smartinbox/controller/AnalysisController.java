package com.clinevo.smartinbox.controller;

import com.clinevo.smartinbox.service.AiService;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

@RestController
@RequestMapping("/api")
@CrossOrigin(origins="*")
public class AnalysisController {

    private final AiService aiService;

    public AnalysisController(AiService aiService) {
        this.aiService = aiService;
    }

    @GetMapping("/health")
    public Object health() {
        return java.util.Map.of(
            "status","UP",
            "service","Clinevo Smart Inbox Backend"
        );
    }

    @PostMapping(value="/analyze", consumes=MediaType.MULTIPART_FORM_DATA_VALUE)
    public Object analyze(@RequestParam("file") MultipartFile file)
            throws Exception {
        return aiService.analyze(file.getBytes(), file.getOriginalFilename());
    }

    @PostMapping(value="/analyze-batch", consumes=MediaType.MULTIPART_FORM_DATA_VALUE)
    public Object analyzeBatch(@RequestParam("files") java.util.List<MultipartFile> files)
            throws Exception {
        return aiService.analyzeBatch(files);
    }
}

