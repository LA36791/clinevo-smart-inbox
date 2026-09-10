package com.clinevo.smartinbox.repository;

import com.clinevo.smartinbox.model.EmailMessage;
import org.springframework.data.jpa.repository.JpaRepository;

public interface EmailMessageRepository extends JpaRepository<EmailMessage,Long> {}
