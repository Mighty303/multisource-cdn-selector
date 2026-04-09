variable "project_id" {
  description = "GCP project ID"
  type        = string
  default     = "cmpt471-cdn-project"
}

variable "credentials_file" {
  description = "Path to the GCP service account key JSON file"
  type        = string
  default     = "../key.json"
}

variable "selector_mode" {
  description = "Selector algorithm: adaptive | random | round_robin"
  type        = string
  default     = "adaptive"
}

variable "weight_latency" {
  description = "Adaptive scoring weight for latency (higher = penalizes latency more)"
  type        = number
  default     = 0.65
}

variable "weight_load" {
  description = "Adaptive scoring weight for load"
  type        = number
  default     = 0.25
}

variable "weight_throughput" {
  description = "Adaptive scoring weight for throughput (higher = rewards throughput more)"
  type        = number
  default     = 0.10
}

variable "probe_timeout_seconds" {
  description = "Per-origin probe timeout in seconds"
  type        = number
  default     = 2.0
}

variable "probe_ttl_seconds" {
  description = "How long to cache probe results before re-probing"
  type        = number
  default     = 5.0
}

variable "probe_sample_bytes" {
  description = "Bytes to download for throughput probe"
  type        = number
  default     = 262144
}

variable "selector_failure_duration" {
  description = "Default forced-offline duration in seconds for /admin/failure endpoint"
  type        = number
  default     = 8
}
