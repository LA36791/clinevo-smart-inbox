package com.clinevo.smartinbox.model;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name="EMAIL_MESSAGE")
public class EmailMessage {
    @Id @GeneratedValue(strategy=GenerationType.IDENTITY)
    private Long id;

    private String sender;
    private String subject;

    @Lob
    private String body;

    private LocalDateTime receivedAt;
    private String status;

    public Long getId(){return id;}
    public String getSender(){return sender;}
    public void setSender(String v){sender=v;}
    public String getSubject(){return subject;}
    public void setSubject(String v){subject=v;}
    public String getBody(){return body;}
    public void setBody(String v){body=v;}
    public LocalDateTime getReceivedAt(){return receivedAt;}
    public void setReceivedAt(LocalDateTime v){receivedAt=v;}
    public String getStatus(){return status;}
    public void setStatus(String v){status=v;}
}
