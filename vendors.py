# vendors.py — CloudMatch vendor knowledge base & test scenarios
# Vendors: AWS · GCP · Azure only
# Import in app.py: from vendors import VENDORS, TEST_SCENARIOS, BASELINE_PRICING

BASELINE_PRICING = {
    "aws": {
        "compute":  {"small": 0.0104, "medium": 0.0416, "large": 0.1664},
        "storage":  0.023, "network": 0.09,
        "database": {"small": 0.017, "medium": 0.068, "large": 0.272},
    },
    "gcp": {
        "compute":  {"small": 0.0095, "medium": 0.0380, "large": 0.1520},
        "storage":  0.020, "network": 0.08,
        "database": {"small": 0.015, "medium": 0.060, "large": 0.240},
    },
    "azure": {
        "compute":  {"small": 0.0112, "medium": 0.0448, "large": 0.1792},
        "storage":  0.018, "network": 0.087,
        "database": {"small": 0.018, "medium": 0.072, "large": 0.288},
    },
}

VENDORS = {
    "aws": {
        "name": "Amazon Web Services", "logo": "AWS", "color": "#FF9900",
        "strengths": ["Widest service catalog", "Global reach", "Mature ecosystem", "Best ML services"],
        "weaknesses": ["Complex pricing", "Steep learning curve", "Cost management difficult"],
        "features": {
            "regions": 31, "services": 200, "sla_uptime": 99.99,
            "free_tier": True, "ml_services": True, "serverless": True,
            "kubernetes": True, "cdn": True,
            "compliance": ["HIPAA", "PCI-DSS", "SOC2", "ISO27001", "GDPR", "FedRAMP"],
        },
        "scores": {
            "reliability": 9.5, "performance": 9.2, "security": 9.4,
            "support": 8.8, "innovation": 9.6, "documentation": 9.0, "community": 9.5,
        },
    },
    "gcp": {
        "name": "Google Cloud Platform", "logo": "GCP", "color": "#4285F4",
        "strengths": ["Best data analytics", "Kubernetes native", "AI/ML leadership", "Competitive pricing"],
        "weaknesses": ["Fewer enterprise features", "Smaller partner ecosystem", "Less mature support"],
        "features": {
            "regions": 35, "services": 150, "sla_uptime": 99.99,
            "free_tier": True, "ml_services": True, "serverless": True,
            "kubernetes": True, "cdn": True,
            "compliance": ["HIPAA", "PCI-DSS", "SOC2", "ISO27001", "GDPR"],
        },
        "scores": {
            "reliability": 9.3, "performance": 9.4, "security": 9.3,
            "support": 8.5, "innovation": 9.7, "documentation": 8.8, "community": 8.9,
        },
    },
    "azure": {
        "name": "Microsoft Azure", "logo": "AZ", "color": "#0078D4",
        "strengths": ["Best enterprise integration", "Hybrid cloud leader", "Microsoft ecosystem", "Strong compliance"],
        "weaknesses": ["Complex portal", "Inconsistent performance", "Pricing complexity"],
        "features": {
            "regions": 60, "services": 200, "sla_uptime": 99.99,
            "free_tier": True, "ml_services": True, "serverless": True,
            "kubernetes": True, "cdn": True,
            "compliance": ["HIPAA", "PCI-DSS", "SOC2", "ISO27001", "GDPR", "FedRAMP", "DoD CC SRG"],
        },
        "scores": {
            "reliability": 9.2, "performance": 9.0, "security": 9.6,
            "support": 9.1, "innovation": 9.0, "documentation": 9.2, "community": 9.0,
        },
    },
}

TEST_SCENARIOS = [
    {
        "id": 1, "name": "Healthcare Startup — HIPAA + FedRAMP",
        "description": "Small healthcare startup; must comply with HIPAA and FedRAMP; high security priority.",
        "expected_vendor": "azure",
        "rationale": "Azure is the only vendor with both HIPAA and FedRAMP; its security score (9.6) is highest.",
        "requirements": {
            "workload": {"compute_size":"small","compute_hours":730,"storage_gb":50,"network_gb":20,"db_instances":1,"db_size":"small"},
            "max_budget":200,"required_compliance":["HIPAA","FedRAMP"],
            "needs_ml":False,"needs_kubernetes":False,"needs_serverless":False,
            "cost_weight":0.10,"reliability_weight":0.10,"performance_weight":0.05,
            "security_weight":0.45,"support_weight":0.10,"innovation_weight":0.05,"compliance_weight":0.15,
        },
    },
    {
        "id": 2, "name": "AI / ML Research Lab",
        "description": "University research team running large GPU training jobs; innovation and ML services are paramount.",
        "expected_vendor": "gcp",
        "rationale": "GCP leads in AI/ML innovation (9.7); innovation_weight=0.50 decisively favours GCP.",
        "requirements": {
            "workload": {"compute_size":"large","compute_hours":500,"storage_gb":500,"network_gb":100,"db_instances":1,"db_size":"medium"},
            "max_budget":2000,"required_compliance":[],
            "needs_ml":True,"needs_kubernetes":True,"needs_serverless":False,
            "cost_weight":0.05,"reliability_weight":0.10,"performance_weight":0.20,
            "security_weight":0.05,"support_weight":0.05,"innovation_weight":0.50,"compliance_weight":0.05,
        },
    },
    {
        "id": 3, "name": "Enterprise SAP Migration",
        "description": "Large enterprise migrating SAP workloads; needs hybrid connectivity and enterprise support.",
        "expected_vendor": "azure",
        "rationale": "Azure's support score (9.1) is highest; support_weight=0.35 rewards enterprise support quality.",
        "requirements": {
            "workload": {"compute_size":"large","compute_hours":730,"storage_gb":2000,"network_gb":500,"db_instances":3,"db_size":"large"},
            "max_budget":5000,"required_compliance":["SOC2","ISO27001"],
            "needs_ml":False,"needs_kubernetes":False,"needs_serverless":False,
            "cost_weight":0.05,"reliability_weight":0.20,"performance_weight":0.10,
            "security_weight":0.20,"support_weight":0.35,"innovation_weight":0.05,"compliance_weight":0.05,
        },
    },
    {
        "id": 4, "name": "E-Commerce Platform — PCI-DSS",
        "description": "Mid-size e-commerce platform handling card payments; PCI-DSS mandatory; high traffic spikes.",
        "expected_vendor": "aws",
        "rationale": "AWS leads in reliability (9.5); reliability_weight=0.40 rewards its 99.99% uptime track record.",
        "requirements": {
            "workload": {"compute_size":"medium","compute_hours":730,"storage_gb":300,"network_gb":200,"db_instances":2,"db_size":"medium"},
            "max_budget":1000,"required_compliance":["PCI-DSS","SOC2"],
            "needs_ml":False,"needs_kubernetes":True,"needs_serverless":True,
            "cost_weight":0.10,"reliability_weight":0.40,"performance_weight":0.20,
            "security_weight":0.15,"support_weight":0.05,"innovation_weight":0.05,"compliance_weight":0.05,
        },
    },
    {
        "id": 5, "name": "Big Data Analytics Pipeline",
        "description": "Data engineering team running Spark pipelines; performance and innovation are key.",
        "expected_vendor": "gcp",
        "rationale": "GCP's performance (9.4) and innovation (9.7) lead; innovation_weight=0.40 favours GCP.",
        "requirements": {
            "workload": {"compute_size":"large","compute_hours":400,"storage_gb":5000,"network_gb":300,"db_instances":1,"db_size":"large"},
            "max_budget":3000,"required_compliance":["GDPR"],
            "needs_ml":True,"needs_kubernetes":True,"needs_serverless":False,
            "cost_weight":0.05,"reliability_weight":0.10,"performance_weight":0.30,
            "security_weight":0.05,"support_weight":0.05,"innovation_weight":0.40,"compliance_weight":0.05,
        },
    },
    {
        "id": 6, "name": "Government Defence App — FedRAMP + DoD",
        "description": "US government contractor; FedRAMP and DoD CC SRG mandatory.",
        "expected_vendor": "azure",
        "rationale": "Azure is the only vendor with DoD CC SRG; hard compliance gate eliminates all others.",
        "requirements": {
            "workload": {"compute_size":"medium","compute_hours":730,"storage_gb":200,"network_gb":100,"db_instances":2,"db_size":"medium"},
            "max_budget":2000,"required_compliance":["FedRAMP","DoD CC SRG"],
            "needs_ml":False,"needs_kubernetes":True,"needs_serverless":False,
            "cost_weight":0.05,"reliability_weight":0.15,"performance_weight":0.10,
            "security_weight":0.40,"support_weight":0.10,"innovation_weight":0.05,"compliance_weight":0.15,
        },
    },
    {
        "id": 7, "name": "Global SaaS — High Reliability",
        "description": "SaaS serving 50 countries; reliability and global reach are paramount.",
        "expected_vendor": "aws",
        "rationale": "AWS leads in reliability (9.5); reliability_weight=0.50 decisively rewards its global uptime.",
        "requirements": {
            "workload": {"compute_size":"large","compute_hours":730,"storage_gb":1000,"network_gb":500,"db_instances":3,"db_size":"large"},
            "max_budget":8000,"required_compliance":["SOC2","GDPR"],
            "needs_ml":False,"needs_kubernetes":True,"needs_serverless":True,
            "cost_weight":0.05,"reliability_weight":0.50,"performance_weight":0.15,
            "security_weight":0.15,"support_weight":0.10,"innovation_weight":0.03,"compliance_weight":0.02,
        },
    },
    {
        "id": 8, "name": "European Fintech — GDPR + PCI-DSS",
        "description": "European fintech; GDPR and PCI-DSS mandatory; cost-sensitive; high performance.",
        "expected_vendor": "gcp",
        "rationale": "GCP passes compliance gate and has the best performance score; lower pricing favours cost weight.",
        "requirements": {
            "workload": {"compute_size":"medium","compute_hours":730,"storage_gb":150,"network_gb":80,"db_instances":1,"db_size":"medium"},
            "max_budget":400,"required_compliance":["GDPR","PCI-DSS"],
            "needs_ml":False,"needs_kubernetes":False,"needs_serverless":True,
            "cost_weight":0.35,"reliability_weight":0.15,"performance_weight":0.20,
            "security_weight":0.10,"support_weight":0.05,"innovation_weight":0.10,"compliance_weight":0.05,
        },
    },
    {
        "id": 9, "name": "IoT Platform — Serverless Events",
        "description": "IoT platform processing millions of sensor events; serverless and performance are key.",
        "expected_vendor": "aws",
        "rationale": "AWS Lambda and IoT Core are the most mature; reliability+performance weights favour AWS.",
        "requirements": {
            "workload": {"compute_size":"medium","compute_hours":400,"storage_gb":200,"network_gb":150,"db_instances":1,"db_size":"small"},
            "max_budget":600,"required_compliance":[],
            "needs_ml":False,"needs_kubernetes":False,"needs_serverless":True,
            "cost_weight":0.10,"reliability_weight":0.30,"performance_weight":0.30,
            "security_weight":0.10,"support_weight":0.10,"innovation_weight":0.07,"compliance_weight":0.03,
        },
    },
    {
        "id": 10, "name": "Kubernetes-Native Microservices",
        "description": "Engineering team building cloud-native microservices; Kubernetes and innovation are priorities.",
        "expected_vendor": "gcp",
        "rationale": "GKE is the original K8s; innovation_weight=0.37 + needs_kubernetes bonus decisively favours GCP.",
        "requirements": {
            "workload": {"compute_size":"medium","compute_hours":730,"storage_gb":200,"network_gb":100,"db_instances":2,"db_size":"small"},
            "max_budget":800,"required_compliance":[],
            "needs_ml":False,"needs_kubernetes":True,"needs_serverless":True,
            "cost_weight":0.05,"reliability_weight":0.15,"performance_weight":0.30,
            "security_weight":0.05,"support_weight":0.05,"innovation_weight":0.37,"compliance_weight":0.03,
        },
    },
    {
        "id": 11, "name": "Enterprise Microsoft 365 Integration",
        "description": "Enterprise app deeply integrated with Teams, Active Directory, and Power BI.",
        "expected_vendor": "azure",
        "rationale": "Azure has the highest support score (9.1); support_weight=0.40 rewards enterprise integration depth.",
        "requirements": {
            "workload": {"compute_size":"medium","compute_hours":730,"storage_gb":300,"network_gb":100,"db_instances":2,"db_size":"medium"},
            "max_budget":1500,"required_compliance":["SOC2"],
            "needs_ml":False,"needs_kubernetes":False,"needs_serverless":True,
            "cost_weight":0.05,"reliability_weight":0.15,"performance_weight":0.10,
            "security_weight":0.20,"support_weight":0.40,"innovation_weight":0.05,"compliance_weight":0.05,
        },
    },
    {
        "id": 12, "name": "Balanced General-Purpose Workload",
        "description": "Mid-size company with no special requirements; wants the most well-rounded provider.",
        "expected_vendor": "aws",
        "rationale": "AWS scores highest overall when reliability and support are weighted moderately; broadest service catalog.",
        "requirements": {
            "workload": {"compute_size":"medium","compute_hours":730,"storage_gb":100,"network_gb":50,"db_instances":1,"db_size":"small"},
            "max_budget":500,"required_compliance":[],
            "needs_ml":False,"needs_kubernetes":False,"needs_serverless":False,
            "cost_weight":0.15,"reliability_weight":0.25,"performance_weight":0.15,
            "security_weight":0.15,"support_weight":0.15,"innovation_weight":0.10,"compliance_weight":0.05,
        },
    },
]

VALID_SIZES      = {"small", "medium", "large"}
VALID_COMPLIANCE = {"HIPAA", "PCI-DSS", "SOC2", "ISO27001", "GDPR", "FedRAMP", "DoD CC SRG"}
