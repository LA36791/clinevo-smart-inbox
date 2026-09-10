package com.clinevo.smartinbox.service;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestTemplate;

@Service
public class AiService {

    @Value("${ai.service.url}")
    private String aiUrl;

    private final RestTemplate restTemplate = new RestTemplate();

    public Object analyze(byte[] file, String filename) {

        ByteArrayResource resource = new ByteArrayResource(file) {
            @Override
            public String getFilename() {
                return filename;
            }
        };

        MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
        body.add("file", resource);

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.MULTIPART_FORM_DATA);

        HttpEntity<MultiValueMap<String, Object>> request =
                new HttpEntity<>(body, headers);

        ResponseEntity<Object> response = restTemplate.postForEntity(
                aiUrl + "/analyze-document",
                request,
                Object.class
        );

        return response.getBody();
    }
}
