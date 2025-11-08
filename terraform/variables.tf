variable "project_name" {
  description = "Name prefix for all resources"
  type        = string
  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.project_name))
    error_message = "Project name must contain only lowercase letters, numbers, and hyphens."
  }
}

variable "environment" {
  description = "Environment name (dev, test, prod)"
  type        = string
  validation {
    condition     = contains(["dev", "test", "prod"], var.environment)
    error_message = "Environment must be one of: dev, test, prod."
  }
}

variable "bedrock_model_id" {
  description = "Bedrock model ID"
  type        = string
  default     = "us.amazon.nova-micro-v1:0"
}

variable "lambda_timeout" {
  description = "Lambda function timeout in seconds"
  type        = number
  default     = 60
}

variable "api_throttle_burst_limit" {
  description = "API Gateway throttle burst limit"
  type        = number
  default     = 10
}

variable "api_throttle_rate_limit" {
  description = "API Gateway throttle rate limit"
  type        = number
  default     = 5
}

variable "use_custom_domain" {
  description = "Attach a custom domain to CloudFront"
  type        = bool
  default     = false
}

variable "root_domain" {
  description = "Apex domain name, e.g. mydomain.com"
  type        = string
  default     = ""
}

variable "sender_name" {
  description = "Display name used for outbound emails"
  type        = string
  default     = "Darin's Digital Twin"
}

variable "sender_email" {
  description = "From email address used for outbound emails"
  type        = string
  default     = "darinwilliams50@gmail.com"
}


variable "brevo_api_url" {
  description = "Brevo SMTP API URL"
  type        = string
  default     = "https://api.brevo.com/v3/smtp/email"
}

variable "brevo_api_key" {
  description = "Brevo API key"
  type        = string
  sensitive   = true
}


variable "max_request_per_hour" {
  description = "Max Request Per Hour"
  type        = number
  default     = 2
}

variable "min_captcha_score" {
  description = "Min Captcha Score"
  type        = number
  default     = 0.5
}

variable "next_public_site_key" {
  description = "Next Publc Site Key"
  type        = string
  sensitive   = true
}

variable "recaptcha_secret_key" {
  description = "Recaptcha Secret Key"
  type        = string
  sensitive   = true
}

variable "recaptcha_verify_url" {
  description = "Recaptcha Verify URL"
  type        = string
  default     = "https://www.google.com/recaptcha/api/siteverify"
}

variable "resume_name" {
  description = "Resume Name"
  type        = string
  default     = "resume.pdf"
}



