# Kubernetes Jobs Investigation Plan

## Long-Running Security Tools Execution

---

## Executive Summary

This plan investigates implementing Kubernetes Jobs for running long-running security tools (Burp Suite, ZAP, extensive scans) in a resilient, scalable manner. The system will support triggering jobs from agents, polling for status updates, and collecting results asynchronously.

---

## Problem Statement

### Current Architecture Limitations

1. **In-process execution**: All scans run within the main application container
2. **Resource constraints**: Long-running tools can exhaust container resources
3. **No fault tolerance**: Application restarts lose running scan state
4. **Limited concurrency**: Bounded by single container's resources
5. **Blocking operations**: Long scans block API responses
6. **No priority scheduling**: All scans compete for same resources

### Target Tools for K8s Jobs

- **Burp Suite Professional** (2-8 hours)
- **OWASP ZAP** full scans (1-4 hours)
- **SQLMap** deep testing (30 min - 2 hours)
- **Nuclei** comprehensive templates (15-60 min)
- **Nmap** extensive port scans (10-30 min)
- **WPScan** full enumeration (5-20 min)
- **Custom fuzzing campaigns** (variable duration)

---

## Proposed Architecture

### High-Level Design

```
┌─────────────────────────────────────────────────────────────┐
│                    Security Agency App                       │
│                    (Main Flask Service)                      │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   REST API   │  │ WebSocket    │  │  Job Manager │      │
│  │   Gateway    │  │   Updates    │  │  Controller  │      │
│  └──────┬───────┘  └──────────────┘  └──────┬───────┘      │
│         │                                     │              │
└─────────┼─────────────────────────────────────┼──────────────┘
          │                                     │
          ▼                                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  Kubernetes Cluster                          │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Job Manager Component                    │  │
│  │                                                        │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐     │  │
│  │  │   Job      │  │   Status   │  │  Result    │     │  │
│  │  │  Creator   │  │   Poller   │  │  Collector │     │  │
│  │  └────────────┘  └────────────┘  └────────────┘     │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Kubernetes Jobs (Ephemeral)              │  │
│  │                                                        │  │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐        │  │
│  │  │ Burp   │ │  ZAP   │ │ SQLMap │ │ Nmap   │  ...   │  │
│  │  │  Job   │ │  Job   │ │  Job   │ │  Job   │        │  │
│  │  └────────┘ └────────┘ └────────┘ └────────┘        │  │
│  │      │          │          │          │               │  │
│  │      └──────────┴──────────┴──────────┘               │  │
│  │                   │                                    │  │
│  │           ┌───────▼────────┐                          │  │
│  │           │  Shared Volume │                          │  │
│  │           │  (Results PVC) │                          │  │
│  │           └────────────────┘                          │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Background Services                      │  │
│  │                                                        │  │
│  │  ┌─────────────────┐  ┌─────────────────┐           │  │
│  │  │  CronJob (Poll) │  │ Event Processor │           │  │
│  │  │  Every 30s      │  │ (Job Lifecycle) │           │  │
│  │  └─────────────────┘  └─────────────────┘           │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                               │
└───────────────────────────────────────────────────────────────┘
          │                                     │
          ▼                                     ▼
┌─────────────────┐                  ┌─────────────────┐
│   PostgreSQL    │                  │  Azure Cosmos   │
│  (Job Metadata) │                  │   (Optional)    │
└─────────────────┘                  └─────────────────┘
```

---

## Implementation Components

### 1. Job Execution Models

#### Model A: Kubernetes Job API (Recommended)

**Characteristics**:

- Native K8s Jobs for each scan
- Job cleanup after completion
- Built-in retry logic
- Resource limits per job

**Pros**:

- Native K8s orchestration
- Excellent fault tolerance
- Resource isolation
- Pod restart on failure
- Clean job history

**Cons**:

- Requires K8s cluster
- More complex setup
- Job creation overhead

#### Model B: Kubernetes CronJob + Queue

**Characteristics**:

- CronJob polls job queue
- Workers process from queue
- Persistent worker pools

**Pros**:

- Simpler job management
- Better for high-frequency jobs
- Lower K8s API overhead

**Cons**:

- Custom queue management
- Less isolation
- Worker pool management

#### Recommendation: **Hybrid Approach**

- Use **Jobs** for long-running, resource-intensive scans (Burp, ZAP)
- Use **CronJob + Queue** for frequent, shorter scans (Nmap, Nikto)

---

### 2. Core Components to Implement

#### 2.1 Job Manager Service

```python
# core/job_manager.py

from kubernetes import client, config
from typing import Dict, Optional, List
from datetime import datetime
from enum import Enum

class JobStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"

class JobManager:
    """
    Manages Kubernetes Jobs for long-running security tools.
    """

    def __init__(self, namespace: str = "security-agency"):
        config.load_incluster_config()  # or load_kube_config() for local dev
        self.batch_v1 = client.BatchV1Api()
        self.core_v1 = client.CoreV1Api()
        self.namespace = namespace

    def create_job(
        self,
        job_name: str,
        tool: str,
        target: str,
        scan_id: str,
        image: str,
        args: List[str],
        timeout_seconds: int = 7200,  # 2 hours default
        cpu_limit: str = "2",
        memory_limit: str = "4Gi",
    ) -> Dict:
        """Create a Kubernetes Job for a security tool."""

    def get_job_status(self, job_name: str) -> JobStatus:
        """Poll job status from Kubernetes API."""

    def get_job_logs(self, job_name: str) -> str:
        """Retrieve logs from completed/running job."""

    def delete_job(self, job_name: str, cascade: bool = True):
        """Clean up completed job and its pods."""

    def list_active_jobs(self) -> List[Dict]:
        """List all active security scanning jobs."""
```

#### 2.2 Job Status Poller

```python
# core/job_poller.py

import asyncio
from typing import Dict, List
from core.job_manager import JobManager, JobStatus
from core.storage import Storage
from core.event_queue import EventQueue

class JobPoller:
    """
    Background service that polls Kubernetes Jobs for status updates.
    """

    def __init__(self, poll_interval: int = 30):
        self.job_manager = JobManager()
        self.storage = Storage()
        self.event_queue = EventQueue()
        self.poll_interval = poll_interval
        self.running = False

    async def start(self):
        """Start the polling loop."""
        self.running = True
        while self.running:
            await self.poll_all_jobs()
            await asyncio.sleep(self.poll_interval)

    async def poll_all_jobs(self):
        """Check status of all active jobs."""
        active_jobs = self.storage.get_active_jobs()

        for job in active_jobs:
            status = self.job_manager.get_job_status(job['k8s_job_name'])

            if status != job['status']:
                # Status changed - update and emit event
                await self._handle_status_change(job, status)

    async def _handle_status_change(self, job: Dict, new_status: JobStatus):
        """Handle job status transitions."""
        # Update database
        self.storage.update_job_status(job['id'], new_status.value)

        # Emit event for real-time updates
        self.event_queue.publish({
            'type': 'job_status_change',
            'job_id': job['id'],
            'scan_id': job['scan_id'],
            'status': new_status.value,
            'timestamp': datetime.utcnow().isoformat()
        })

        # If completed, collect results
        if new_status == JobStatus.COMPLETED:
            await self._collect_results(job)

    async def _collect_results(self, job: Dict):
        """Collect results from completed job."""
        # Read from shared volume or fetch logs
        logs = self.job_manager.get_job_logs(job['k8s_job_name'])

        # Parse and store results
        result = self._parse_tool_output(job['tool'], logs)
        self.storage.save_scan_result(result)

        # Cleanup job
        self.job_manager.delete_job(job['k8s_job_name'])
```

#### 2.3 Enhanced Agent Base Class

```python
# agents/base_agent.py (Enhanced)

from abc import ABC, abstractmethod
from typing import Optional, Dict
from enum import Enum

class ExecutionMode(Enum):
    LOCAL = "local"      # In-process execution
    K8S_JOB = "k8s_job"  # Kubernetes Job
    ASYNC = "async"      # Background async task

class BaseAgent(ABC):

    def __init__(
        self,
        name: str,
        command: str,
        execution_mode: ExecutionMode = ExecutionMode.LOCAL,
        timeout: int = 300,
        requires_k8s: bool = False
    ):
        self.name = name
        self.command = command
        self.execution_mode = execution_mode
        self.timeout = timeout
        self.requires_k8s = requires_k8s

    @abstractmethod
    def build_args(self, target: str) -> list:
        """Build CLI arguments."""
        pass

    def should_use_k8s(self, target: str, options: Dict) -> bool:
        """Determine if this scan should run as K8s Job."""
        # Override in subclasses for intelligent decision
        return self.requires_k8s or self.execution_mode == ExecutionMode.K8S_JOB

    def get_k8s_config(self) -> Dict:
        """Get Kubernetes resource configuration for this tool."""
        return {
            'image': self.get_container_image(),
            'cpu_limit': '2',
            'memory_limit': '4Gi',
            'timeout_seconds': self.timeout,
        }

    @abstractmethod
    def get_container_image(self) -> str:
        """Return container image for K8s execution."""
        pass
```

#### 2.4 Job-Aware Orchestrator

```python
# core/orchestrator.py (Enhanced)

from typing import List, Optional
from core.job_manager import JobManager
from core.models import ScanRequest, ScanResult
from agents.base_agent import ExecutionMode

class Orchestrator:

    def __init__(self):
        self.agents = {...}  # existing agents
        self.job_manager = JobManager()
        self.storage = Storage()

    async def run_scan_async(self, request: ScanRequest) -> List[ScanResult]:
        """Execute scan with intelligent execution mode selection."""
        results = []

        for agent_name in request.requested_agents:
            agent = self.agents[agent_name]

            # Decide execution mode
            if agent.should_use_k8s(request.target, request.options or {}):
                # Run as K8s Job
                job_id = await self._execute_as_k8s_job(
                    agent,
                    request.target,
                    request.id
                )
                results.append({
                    'agent': agent_name,
                    'status': 'job_scheduled',
                    'job_id': job_id,
                    'type': 'async'
                })
            else:
                # Run locally (existing logic)
                result = await agent.run_async(request.target, request.id)
                results.append(result)

        return results

    async def _execute_as_k8s_job(
        self,
        agent,
        target: str,
        scan_id: str
    ) -> str:
        """Execute agent as Kubernetes Job."""
        job_name = f"{agent.name}-{scan_id}-{int(time.time())}"
        args = agent.build_args(target)
        k8s_config = agent.get_k8s_config()

        # Create job record in database
        job_record = {
            'id': str(uuid.uuid4()),
            'scan_id': scan_id,
            'k8s_job_name': job_name,
            'tool': agent.name,
            'target': target,
            'status': 'pending',
            'created_at': datetime.utcnow()
        }
        self.storage.save_job(job_record)

        # Create Kubernetes Job
        self.job_manager.create_job(
            job_name=job_name,
            tool=agent.name,
            target=target,
            scan_id=scan_id,
            image=k8s_config['image'],
            args=args,
            timeout_seconds=k8s_config['timeout_seconds'],
            cpu_limit=k8s_config['cpu_limit'],
            memory_limit=k8s_config['memory_limit']
        )

        return job_record['id']
```

---

### 3. Database Schema Updates

```sql
-- New table for K8s job tracking
CREATE TABLE k8s_jobs (
    id UUID PRIMARY KEY,
    scan_id VARCHAR(255) NOT NULL,
    k8s_job_name VARCHAR(255) UNIQUE NOT NULL,
    tool VARCHAR(50) NOT NULL,
    target VARCHAR(512) NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    result_path VARCHAR(512),
    metadata JSONB,
    INDEX idx_scan_id (scan_id),
    INDEX idx_status (status),
    INDEX idx_k8s_job_name (k8s_job_name)
);

-- Update scan_results to link to jobs
ALTER TABLE scan_results ADD COLUMN job_id UUID REFERENCES k8s_jobs(id);
```

---

### 4. API Endpoints

```python
# New endpoints in app.py

@app.route("/jobs/<job_id>", methods=["GET"])
def get_job_status(job_id):
    """Get status of a specific job."""
    job = storage.get_job(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    # Get live status from K8s
    if job['status'] in ['pending', 'running']:
        live_status = job_manager.get_job_status(job['k8s_job_name'])
        job['status'] = live_status.value

    return jsonify(job)

@app.route("/jobs", methods=["GET"])
def list_jobs():
    """List all jobs with optional filters."""
    status = request.args.get('status')
    scan_id = request.args.get('scan_id')
    limit = int(request.args.get('limit', 50))

    jobs = storage.list_jobs(
        status=status,
        scan_id=scan_id,
        limit=limit
    )
    return jsonify(jobs)

@app.route("/jobs/<job_id>/logs", methods=["GET"])
def get_job_logs(job_id):
    """Stream logs from a running or completed job."""
    job = storage.get_job(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    logs = job_manager.get_job_logs(job['k8s_job_name'])
    return Response(logs, mimetype='text/plain')

@app.route("/jobs/<job_id>/cancel", methods=["POST"])
def cancel_job(job_id):
    """Cancel a running job."""
    job = storage.get_job(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    job_manager.delete_job(job['k8s_job_name'], cascade=True)
    storage.update_job_status(job_id, 'cancelled')

    return jsonify({"status": "cancelled"})
```

---

### 5. Kubernetes Manifests

#### 5.1 Service Account & RBAC

```yaml
# k8s/rbac.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: security-agency-sa
  namespace: security-agency
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: job-manager-role
  namespace: security-agency
rules:
  - apiGroups: ["batch"]
    resources: ["jobs"]
    verbs: ["create", "get", "list", "delete", "watch"]
  - apiGroups: [""]
    resources: ["pods", "pods/log"]
    verbs: ["get", "list", "watch"]
  - apiGroups: [""]
    resources: ["pods/status"]
    verbs: ["get"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: job-manager-binding
  namespace: security-agency
subjects:
  - kind: ServiceAccount
    name: security-agency-sa
roleRef:
  kind: Role
  name: job-manager-role
  apiGroup: rbac.authorization.k8s.io
```

#### 5.2 Job Template Example

```yaml
# k8s/job-templates/burpsuite-job.yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: burpsuite-{{ scan_id }}
  namespace: security-agency
  labels:
    app: security-agency
    tool: burpsuite
    scan-id: "{{ scan_id }}"
spec:
  ttlSecondsAfterFinished: 3600 # Cleanup after 1 hour
  backoffLimit: 2
  activeDeadlineSeconds: 14400 # 4 hour timeout
  template:
    metadata:
      labels:
        app: security-agency
        tool: burpsuite
    spec:
      restartPolicy: OnFailure
      serviceAccountName: security-agency-sa
      containers:
        - name: burpsuite
          image: security-agency/burpsuite:latest
          args: ["{{ target }}", "--scan-id", "{{ scan_id }}"]
          resources:
            requests:
              memory: "4Gi"
              cpu: "2"
            limits:
              memory: "8Gi"
              cpu: "4"
          volumeMounts:
            - name: results
              mountPath: /results
          env:
            - name: SCAN_ID
              value: "{{ scan_id }}"
            - name: TARGET
              value: "{{ target }}"
      volumes:
        - name: results
          persistentVolumeClaim:
            claimName: scan-results-pvc
```

#### 5.3 CronJob for Status Polling

```yaml
# k8s/cronjobs/job-poller.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: job-status-poller
  namespace: security-agency
spec:
  schedule: "*/1 * * * *" # Every minute
  concurrencyPolicy: Forbid
  jobTemplate:
    spec:
      template:
        spec:
          restartPolicy: OnFailure
          serviceAccountName: security-agency-sa
          containers:
            - name: poller
              image: security-agency/app:latest
              command: ["python", "scripts/poll_jobs.py"]
              env:
                - name: DATABASE_URL
                  valueFrom:
                    secretKeyRef:
                      name: db-credentials
                      key: connection-string
```

---

### 6. Container Images for Tools

#### Directory Structure

```
docker-images/
├── base/
│   └── Dockerfile              # Base image with common tools
├── burpsuite/
│   ├── Dockerfile
│   ├── burp-config.json
│   └── entrypoint.sh
├── zap/
│   ├── Dockerfile
│   └── zap-scan.py
├── sqlmap/
│   └── Dockerfile
├── nmap/
│   └── Dockerfile
└── nuclei/
    └── Dockerfile
```

#### Example: Burp Suite Container

```dockerfile
# docker-images/burpsuite/Dockerfile
FROM openjdk:11-jre-slim

RUN apt-get update && apt-get install -y \
    curl \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Install Burp Suite (Requires license)
COPY burpsuite_pro.jar /opt/burp/burpsuite.jar
COPY burp-config.json /opt/burp/config.json

# Install result uploader
COPY entrypoint.sh /opt/burp/
RUN chmod +x /opt/burp/entrypoint.sh

WORKDIR /opt/burp
ENTRYPOINT ["/opt/burp/entrypoint.sh"]
```

```bash
#!/bin/bash
# docker-images/burpsuite/entrypoint.sh

TARGET=$1
SCAN_ID=$2

echo "Starting Burp Suite scan for $TARGET (Scan ID: $SCAN_ID)"

# Run Burp Suite
java -jar -Xmx4g /opt/burp/burpsuite.jar \
    --project-file=/results/${SCAN_ID}.burp \
    --config-file=/opt/burp/config.json \
    --target=$TARGET \
    --output=/results/${SCAN_ID}-report.html

echo "Scan completed. Results saved to /results/${SCAN_ID}-report.html"

# Upload results to storage service (optional)
# python3 /opt/burp/upload_results.py ${SCAN_ID}

exit 0
```

---

## Implementation Phases

### Phase 1: Foundation (Week 1-2)

**Goals**: Basic K8s Job execution framework

**Tasks**:

- [ ] Set up K8s cluster (local: minikube/kind, prod: AKS/EKS/GKE)
- [ ] Implement JobManager class
- [ ] Create RBAC resources
- [ ] Database schema updates
- [ ] Basic job creation/deletion
- [ ] Simple Nmap job as proof of concept

**Deliverables**:

- Working K8s job execution for Nmap
- API endpoint to create job
- Job status tracking in database

---

### Phase 2: Status Polling & Results (Week 3)

**Goals**: Automated status updates and result collection

**Tasks**:

- [ ] Implement JobPoller background service
- [ ] Create CronJob for polling
- [ ] Shared volume for results (PVC)
- [ ] Result parsing and storage
- [ ] WebSocket for real-time updates
- [ ] Job cleanup logic

**Deliverables**:

- Automated job status updates
- Real-time status WebSocket endpoint
- Result collection pipeline

---

### Phase 3: Tool Integration (Week 4-5)

**Goals**: Add support for major tools

**Tasks**:

- [ ] Create Burp Suite container image
- [ ] Create ZAP container image
- [ ] Create SQLMap container image
- [ ] Create Nuclei container image
- [ ] Tool-specific result parsers
- [ ] Enhanced agents with K8s support

**Deliverables**:

- 4+ tools running as K8s Jobs
- Unified result format
- Tool-specific configuration

---

### Phase 4: Advanced Features (Week 6-8)

**Goals**: Production-ready features

**Tasks**:

- [ ] Job priority and queueing
- [ ] Resource quota management
- [ ] Job retry logic with backoff
- [ ] Timeout handling
- [ ] Job cancellation
- [ ] Historical job metrics
- [ ] Cost tracking per job
- [ ] Multi-cluster support (optional)

**Deliverables**:

- Production-grade job scheduling
- Comprehensive monitoring
- Cost optimization

---

## Technical Considerations

### 1. Resource Management

#### Resource Limits per Tool

```python
TOOL_RESOURCES = {
    'burpsuite': {
        'cpu': {'request': '2', 'limit': '4'},
        'memory': {'request': '4Gi', 'limit': '8Gi'},
        'timeout': 14400  # 4 hours
    },
    'zap': {
        'cpu': {'request': '1', 'limit': '2'},
        'memory': {'request': '2Gi', 'limit': '4Gi'},
        'timeout': 7200  # 2 hours
    },
    'sqlmap': {
        'cpu': {'request': '500m', 'limit': '1'},
        'memory': {'request': '512Mi', 'limit': '1Gi'},
        'timeout': 3600  # 1 hour
    },
    # ... more tools
}
```

#### Cluster Sizing Recommendations

- **Development**: 3 nodes, 4 CPU, 8GB RAM each
- **Production**: 5+ nodes, 8 CPU, 16GB RAM each
- **Auto-scaling**: Based on pending jobs queue

---

### 2. Storage Strategy

#### Option A: Persistent Volume Claims (PVC)

**Pros**:

- Simple to implement
- Native K8s storage
- Works across pods

**Cons**:

- Volume size limits
- Cleanup required
- Performance varies

#### Option B: Object Storage (S3/Azure Blob)

**Pros**:

- Unlimited storage
- Built-in lifecycle policies
- Better for large results
- Direct web access

**Cons**:

- External dependency
- Credentials management
- Slight latency

**Recommendation**: Use both

- PVC for in-progress results
- Object storage for long-term archival
- Automatic upload on job completion

---

### 3. Security Considerations

#### Network Policies

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: scan-jobs-policy
  namespace: security-agency
spec:
  podSelector:
    matchLabels:
      app: security-agency
  policyTypes:
    - Ingress
    - Egress
  ingress: [] # No ingress to scan jobs
  egress:
    - to:
        - podSelector: {} # Allow to other pods in namespace
    - ports:
        - port: 53 # DNS
          protocol: UDP
    - ports:
        - port: 443 # HTTPS for scanning targets
          protocol: TCP
```

#### Secrets Management

- Use Kubernetes Secrets for credentials
- Consider Vault/Azure Key Vault integration
- Rotate API keys regularly
- Never log sensitive data

---

### 4. Monitoring & Observability

#### Metrics to Track

```python
METRICS = {
    'jobs_created_total': Counter('Total jobs created'),
    'jobs_completed_total': Counter('Total jobs completed'),
    'jobs_failed_total': Counter('Total jobs failed'),
    'job_duration_seconds': Histogram('Job execution time'),
    'job_queue_length': Gauge('Pending jobs count'),
    'active_jobs': Gauge('Currently running jobs'),
    'tool_usage': Counter('Per-tool execution count'),
}
```

#### Logging Strategy

- Structured JSON logs
- Correlation IDs across services
- Job lifecycle events
- Error tracking with Sentry/Datadog

---

### 5. Cost Optimization

#### Strategies

1. **Job TTL**: Auto-delete completed jobs after 1 hour
2. **Spot Instances**: Use preemptible nodes for non-critical scans
3. **Right-sizing**: Monitor actual resource usage, adjust limits
4. **Scheduling**: Run large scans during off-peak hours
5. **Caching**: Cache results for repeat targets

---

## Development Roadmap

### Prerequisites

```bash
# Install Kubernetes Python client
pip install kubernetes

# Install async support
pip install aiohttp aiojobs

# Install monitoring
pip install prometheus-client
```

### Local Development Setup

#### 1. Start Local K8s Cluster

```bash
# Using kind (Kubernetes in Docker)
kind create cluster --name security-agency

# Or using minikube
minikube start --cpus=4 --memory=8192
```

#### 2. Deploy Base Infrastructure

```bash
# Create namespace
kubectl create namespace security-agency

# Deploy RBAC
kubectl apply -f k8s/rbac.yaml

# Create PVC for results
kubectl apply -f k8s/storage.yaml

# Deploy app with K8s access
kubectl apply -f k8s/deployment.yaml
```

#### 3. Test Job Creation

```python
# test_k8s_jobs.py
from core.job_manager import JobManager

manager = JobManager(namespace='security-agency')

job_id = manager.create_job(
    job_name='nmap-test-001',
    tool='nmap',
    target='scanme.nmap.org',
    scan_id='test-001',
    image='security-agency/nmap:latest',
    args=['-sV', 'scanme.nmap.org'],
    timeout_seconds=300
)

print(f"Job created: {job_id}")
```

---

## Integration Points

### 1. Orchestrator Integration

```python
# Update decision engine to choose execution mode
class DecisionEngine:

    def choose_execution_mode(
        self,
        agent: str,
        target: str,
        priority: int
    ) -> ExecutionMode:
        """Intelligent execution mode selection."""

        # Long-running tools → K8s Jobs
        if agent in ['burpsuite', 'zap']:
            return ExecutionMode.K8S_JOB

        # High priority → Local (faster startup)
        if priority > 8:
            return ExecutionMode.LOCAL

        # Default to async for medium scans
        return ExecutionMode.ASYNC
```

### 2. Frontend Updates

```javascript
// frontend/job-status.js

async function pollJobStatus(jobId) {
  const response = await fetch(`/jobs/${jobId}`);
  const job = await response.json();

  updateJobUI(job);

  // Continue polling if still running
  if (["pending", "running"].includes(job.status)) {
    setTimeout(() => pollJobStatus(jobId), 5000);
  }
}

// WebSocket for real-time updates (preferred)
const ws = new WebSocket("ws://localhost:8000/ws/jobs");
ws.onmessage = (event) => {
  const update = JSON.parse(event.data);
  if (update.type === "job_status_change") {
    updateJobUI(update.job);
  }
};
```

---

## Testing Strategy

### Unit Tests

```python
# tests/test_job_manager.py

def test_create_job():
    manager = JobManager()
    job = manager.create_job(...)
    assert job['status'] == 'pending'

def test_job_status_polling():
    manager = JobManager()
    status = manager.get_job_status('test-job')
    assert status in [JobStatus.PENDING, JobStatus.RUNNING, ...]
```

### Integration Tests

```python
# tests/integration/test_k8s_workflow.py

async def test_full_job_lifecycle():
    # Create job
    job_id = await orchestrator.execute_job(...)

    # Poll until completion
    while True:
        status = await get_job_status(job_id)
        if status == 'completed':
            break
        await asyncio.sleep(5)

    # Verify results
    results = await get_job_results(job_id)
    assert results is not None
```

---

## Migration Strategy

### Backward Compatibility

- Keep local execution as default
- Gradual rollout per tool
- Feature flag: `USE_K8S_JOBS=true`
- Fallback to local on K8s unavailable

### Deployment Plan

1. **Week 1**: Deploy to dev environment
2. **Week 2**: Internal testing with Nmap
3. **Week 3**: Add Burp Suite, monitor
4. **Week 4**: Production rollout (20% traffic)
5. **Week 5**: Increase to 100% if stable

---

## Success Metrics

### KPIs

1. **Scan Completion Rate**: >95% jobs complete successfully
2. **Average Scan Time**: <10% increase vs local
3. **Concurrent Scans**: 10x increase in capacity
4. **System Uptime**: 99.9% availability
5. **Cost per Scan**: <$0.50 per job

### Monitoring Dashboards

- Active jobs count
- Job success/failure rates
- Resource utilization
- Queue depth
- Cost per tool

---

## Risk Mitigation

### Identified Risks

| Risk                     | Impact | Mitigation                             |
| ------------------------ | ------ | -------------------------------------- |
| K8s cluster downtime     | High   | Multi-AZ deployment, fallback to local |
| Job stuck in running     | Medium | Timeout enforcement, health checks     |
| Resource exhaustion      | High   | Quotas, auto-scaling, queue limits     |
| Result storage full      | Medium | Lifecycle policies, compression        |
| Security breach via scan | High   | Network policies, sandboxing           |

---

## Open Questions

1. **Multi-tenancy**: How to isolate scans between different users/orgs?
2. **Licensing**: How to handle Burp Suite Pro license in containers?
3. **Compliance**: What audit logs are required for security scans?
4. **Performance**: What's acceptable latency for job status updates?
5. **Scaling**: When to add cluster nodes vs queue jobs?

---

## Next Steps

### Immediate Actions (This Week)

1. [ ] Set up local K8s cluster (kind/minikube)
2. [ ] Create proof-of-concept with Nmap Job
3. [ ] Implement basic JobManager class
4. [ ] Design database schema
5. [ ] Document API contracts

### Research Required

- [ ] Evaluate K8s operators for job management
- [ ] Compare storage solutions (PVC vs Object Storage)
- [ ] Research Burp Suite containerization options
- [ ] Review security scanning best practices in K8s
- [ ] Cost analysis for different cloud providers

---

## Conclusion

Implementing Kubernetes Jobs for long-running security tools will significantly improve the scalability, reliability, and user experience of the Security Agency platform. This plan provides a phased approach to implementation with clear milestones and risk mitigation strategies.

**Estimated Total Effort**: 6-8 weeks for full implementation  
**Team Size**: 2-3 engineers  
**Budget**: $5K-10K for infrastructure (development + 3 months production)

---

## References

- [Kubernetes Jobs Documentation](https://kubernetes.io/docs/concepts/workloads/controllers/job/)
- [Kubernetes Python Client](https://github.com/kubernetes-client/python)
- [Flask-SocketIO for WebSockets](https://flask-socketio.readthedocs.io/)
- [Best Practices for K8s Jobs](https://kubernetes.io/docs/concepts/workloads/controllers/job/#job-patterns)

---

_Document Version_: 1.0  
_Last Updated_: January 7, 2026  
_Author_: Security Agency Team  
_Status_: Investigation Phase
