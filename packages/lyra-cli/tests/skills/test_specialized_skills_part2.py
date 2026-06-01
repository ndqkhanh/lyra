"""
Tests for Part 2 Specialized Skills (21 new skills).

Domains covered:
- AI Research (4 skills)
- Cloud Engineering (5 skills)
- Product Management (3 skills)
- Business Analysis (2 skills)
- Brainstorming (4 skills)
- Sales Engineering (3 skills)
"""

import pytest

from lyra_cli.skills.specialized import (
    # AI Research
    PaperAnalyzer,
    ExperimentDesigner,
    ModelEvaluator,
    DataScientist,
    # Cloud Engineering
    AWSArchitect,
    GCPArchitect,
    AzureArchitect,
    K8sOperator,
    TerraformEngineer,
    # Product Management
    ProductManager,
    TechnicalPM,
    ProgramManager,
    # Business Analysis
    BusinessAnalyst,
    RequirementsEngineer,
    # Brainstorming
    IdeationFacilitator,
    ProblemDecomposer,
    CreativeThinking,
    StrategyConsultant,
    # Sales Engineering
    SalesEngineer,
    SolutionConsultant,
    DemoSpecialist,
)


# AI Research Skills Tests
class TestPaperAnalyzer:
    def test_missing_paper_content(self):
        analyzer = PaperAnalyzer()
        result = analyzer.run({"paper_content": ""})
        assert "error" in result
        assert "No paper content provided" in result["error"]

    def test_paper_analysis_structure(self):
        analyzer = PaperAnalyzer()
        result = analyzer.run({
            "paper_content": "Abstract: Novel approach to transformer architecture...",
            "title": "Efficient Transformers"
        })
        assert "title" in result
        assert "contributions" in result
        assert "methodology" in result
        assert "results" in result
        assert "limitations" in result
        assert "future_work" in result


class TestExperimentDesigner:
    def test_missing_hypothesis(self):
        designer = ExperimentDesigner()
        result = designer.run({"research_question": ""})
        assert "error" in result
        assert "No research question provided" in result["error"]

    def test_experiment_design_structure(self):
        designer = ExperimentDesigner()
        result = designer.run({
            "research_question": "Does Model X outperform baseline on task Y?"
        })
        assert "hypothesis" in result
        assert "experiment_type" in result
        assert "variables" in result
        assert "sample_size" in result
        assert "analysis_plan" in result


class TestModelEvaluator:
    def test_missing_model_output(self):
        evaluator = ModelEvaluator()
        result = evaluator.run({"model_name": ""})
        assert "error" in result
        assert "No model name provided" in result["error"]

    def test_evaluation_report_structure(self):
        evaluator = ModelEvaluator()
        result = evaluator.run({
            "model_name": "MyModel",
            "model_type": "classification"
        })
        assert "model_name" in result
        assert "performance_metrics" in result
        assert "error_analysis" in result
        assert "deployment_readiness" in result


class TestDataScientist:
    def test_missing_data_context(self):
        scientist = DataScientist()
        result = scientist.run({"problem_description": ""})
        assert "error" in result
        assert "No problem description provided" in result["error"]

    def test_data_science_plan_structure(self):
        scientist = DataScientist()
        result = scientist.run({
            "problem_description": "Customer churn prediction"
        })
        assert "project_name" in result
        assert "problem_type" in result
        assert "exploration_plan" in result
        assert "feature_engineering" in result
        assert "model_recommendations" in result


# Cloud Engineering Skills Tests
class TestAWSArchitect:
    def test_missing_requirements(self):
        architect = AWSArchitect()
        result = architect.run({"requirements": ""})
        assert "error" in result
        assert "No requirements provided" in result["error"]

    def test_aws_architecture_structure(self):
        architect = AWSArchitect()
        result = architect.run({
            "requirements": "High-availability web application"
        })
        assert "project_name" in result
        assert "services" in result
        assert "architecture_diagram" in result
        assert "cost_optimizations" in result
        assert "security_controls" in result


class TestGCPArchitect:
    def test_missing_requirements(self):
        architect = GCPArchitect()
        result = architect.run({"requirements": ""})
        assert "error" in result
        assert "No requirements provided" in result["error"]

    def test_gcp_architecture_structure(self):
        architect = GCPArchitect()
        result = architect.run({
            "requirements": "Serverless data pipeline"
        })
        assert "project_name" in result
        assert "services" in result
        assert "architecture_diagram" in result
        assert "cost_optimizations" in result


class TestAzureArchitect:
    def test_missing_requirements(self):
        architect = AzureArchitect()
        result = architect.run({"requirements": ""})
        assert "error" in result
        assert "No requirements provided" in result["error"]

    def test_azure_architecture_structure(self):
        architect = AzureArchitect()
        result = architect.run({
            "requirements": "Enterprise microservices platform"
        })
        assert "project_name" in result
        assert "services" in result
        assert "architecture_diagram" in result
        assert "cost_optimizations" in result


class TestK8sOperator:
    def test_missing_cluster_context(self):
        operator = K8sOperator()
        result = operator.run({"application_description": ""})
        assert "error" in result
        assert "No application description provided" in result["error"]

    def test_k8s_operational_plan_structure(self):
        operator = K8sOperator()
        result = operator.run({
            "application_description": "Production web application"
        })
        assert "cluster_name" in result
        assert "resources" in result
        assert "monitoring" in result
        assert "backup_strategy" in result


class TestTerraformEngineer:
    def test_missing_infrastructure_requirements(self):
        engineer = TerraformEngineer()
        result = engineer.run({"infrastructure_description": ""})
        assert "error" in result
        assert "No infrastructure description provided" in result["error"]

    def test_terraform_plan_structure(self):
        engineer = TerraformEngineer()
        result = engineer.run({
            "infrastructure_description": "Multi-region VPC setup"
        })
        assert "project_name" in result
        assert "modules" in result
        assert "directory_structure" in result
        assert "state_management" in result


# Product Management Skills Tests
class TestProductManager:
    def test_missing_product_context(self):
        pm = ProductManager()
        result = pm.run({"product_vision": ""})
        assert "error" in result
        assert "No product vision provided" in result["error"]

    def test_product_plan_structure(self):
        pm = ProductManager()
        result = pm.run({
            "product_vision": "Mobile app for fitness tracking"
        })
        assert "product_name" in result
        assert "vision" in result
        assert "features" in result
        assert "roadmap" in result


class TestTechnicalPM:
    def test_missing_technical_context(self):
        tpm = TechnicalPM()
        result = tpm.run({"technical_requirements": ""})
        assert "error" in result
        assert "No technical requirements provided" in result["error"]

    def test_technical_product_plan_structure(self):
        tpm = TechnicalPM()
        result = tpm.run({
            "technical_requirements": "API platform for developers"
        })
        assert "product_name" in result
        assert "technical_decisions" in result
        assert "api_specifications" in result
        assert "technical_roadmap" in result


class TestProgramManager:
    def test_missing_program_context(self):
        pgm = ProgramManager()
        result = pgm.run({"program_description": ""})
        assert "error" in result
        assert "No program description provided" in result["error"]

    def test_program_plan_structure(self):
        pgm = ProgramManager()
        result = pgm.run({
            "program_description": "Digital transformation initiative"
        })
        assert "program_name" in result
        assert "program_charter" in result
        assert "projects" in result
        assert "program_milestones" in result
        assert "resource_allocation" in result


# Business Analysis Skills Tests
class TestBusinessAnalyst:
    def test_missing_business_problem(self):
        ba = BusinessAnalyst()
        result = ba.run({"business_need": ""})
        assert "error" in result
        assert "No business need provided" in result["error"]

    def test_business_analysis_structure(self):
        ba = BusinessAnalyst()
        result = ba.run({
            "business_need": "Declining customer retention"
        })
        assert "project_name" in result
        assert "business_requirements" in result
        assert "process_flows" in result
        assert "gap_analysis" in result
        assert "recommendations" in result


class TestRequirementsEngineer:
    def test_missing_project_context(self):
        re = RequirementsEngineer()
        result = re.run({"stakeholder_needs": ""})
        assert "error" in result
        assert "No stakeholder needs provided" in result["error"]

    def test_requirements_plan_structure(self):
        re = RequirementsEngineer()
        result = re.run({
            "stakeholder_needs": "E-commerce checkout system"
        })
        assert "project_name" in result
        assert "requirements" in result
        assert "use_cases" in result
        assert "traceability_matrix" in result


# Brainstorming Skills Tests
class TestIdeationFacilitator:
    def test_missing_topic(self):
        facilitator = IdeationFacilitator()
        result = facilitator.run({"problem_statement": ""})
        assert "error" in result
        assert "No problem statement provided" in result["error"]

    def test_ideation_plan_structure(self):
        facilitator = IdeationFacilitator()
        result = facilitator.run({
            "problem_statement": "Sustainable packaging solutions"
        })
        assert "problem_statement" in result
        assert "ideation_sessions" in result
        assert "sample_ideas" in result
        assert "evaluation_criteria" in result


class TestProblemDecomposer:
    def test_missing_problem(self):
        decomposer = ProblemDecomposer()
        result = decomposer.run({"problem_statement": ""})
        assert "error" in result
        assert "No problem statement provided" in result["error"]

    def test_problem_decomposition_structure(self):
        decomposer = ProblemDecomposer()
        result = decomposer.run({
            "problem_statement": "Reduce application latency"
        })
        assert "original_problem" in result
        assert "sub_problems" in result
        assert "root_causes" in result
        assert "solution_approaches" in result


class TestCreativeThinking:
    def test_missing_challenge(self):
        thinker = CreativeThinking()
        result = thinker.run({"challenge": ""})
        assert "error" in result
        assert "No challenge provided" in result["error"]

    def test_creative_thinking_plan_structure(self):
        thinker = CreativeThinking()
        result = thinker.run({
            "challenge": "Improve team collaboration"
        })
        assert "challenge" in result
        assert "creative_exercises" in result
        assert "innovation_opportunities" in result
        assert "breakthrough_ideas" in result


class TestStrategyConsultant:
    def test_missing_business_context(self):
        consultant = StrategyConsultant()
        result = consultant.run({"business_context": ""})
        assert "error" in result
        assert "No business context provided" in result["error"]

    def test_strategic_plan_structure(self):
        consultant = StrategyConsultant()
        result = consultant.run({
            "business_context": "Tech startup entering new market"
        })
        assert "company_name" in result
        assert "swot_analysis" in result
        assert "strategic_options" in result
        assert "recommended_strategy" in result


# Sales Engineering Skills Tests
class TestSalesEngineer:
    def test_missing_customer_context(self):
        se = SalesEngineer()
        result = se.run({"customer_requirements": ""})
        assert "error" in result
        assert "No customer requirements provided" in result["error"]

    def test_sales_engineering_plan_structure(self):
        se = SalesEngineer()
        result = se.run({
            "customer_requirements": "Enterprise customer evaluating our platform"
        })
        assert "customer_name" in result
        assert "technical_solution" in result
        assert "demo_scenarios" in result
        assert "poc_scope" in result


class TestSolutionConsultant:
    def test_missing_client_requirements(self):
        sc = SolutionConsultant()
        result = sc.run({"business_challenges": ""})
        assert "error" in result
        assert "No business challenges provided" in result["error"]

    def test_solution_consulting_plan_structure(self):
        sc = SolutionConsultant()
        result = sc.run({
            "business_challenges": "Cloud migration for legacy systems"
        })
        assert "customer_name" in result
        assert "solution_architecture" in result
        assert "business_value" in result
        assert "roi_analysis" in result


class TestDemoSpecialist:
    def test_missing_demo_context(self):
        ds = DemoSpecialist()
        result = ds.run({"product_name": ""})
        assert "error" in result
        assert "No product name provided" in result["error"]

    def test_demo_plan_structure(self):
        ds = DemoSpecialist()
        result = ds.run({
            "product_name": "Enterprise Platform"
        })
        assert "product_name" in result
        assert "audience_type" in result
        assert "demo_segments" in result
        assert "key_talking_points" in result
