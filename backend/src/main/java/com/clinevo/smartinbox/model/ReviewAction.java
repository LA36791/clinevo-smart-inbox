package com.clinevo.smartinbox.model;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name="REVIEW_ACTION")
public class ReviewAction {
    @Id @GeneratedValue(strategy=GenerationType.IDENTITY)
    private Long id;

    private Long analysisId;
    private String action;
    private String originalCategory;
    private String finalCategory;
    private String reviewer;

    @Column(length=4000)
    private String notes;

    private LocalDateTime actionTimestamp;

    public Long getId(){return id;}
    public Long getAnalysisId(){return analysisId;}
    public void setAnalysisId(Long v){analysisId=v;}
    public String getAction(){return action;}
    public void setAction(String v){action=v;}
    public String getOriginalCategory(){return originalCategory;}
    public void setOriginalCategory(String v){originalCategory=v;}
    public String getFinalCategory(){return finalCategory;}
    public void setFinalCategory(String v){finalCategory=v;}
    public String getReviewer(){return reviewer;}
    public void setReviewer(String v){reviewer=v;}
    public String getNotes(){return notes;}
    public void setNotes(String v){notes=v;}
    public LocalDateTime getActionTimestamp(){return actionTimestamp;}
    public void setActionTimestamp(LocalDateTime v){actionTimestamp=v;}
}
