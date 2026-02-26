"""Structured capability test definitions for Phase 7B."""

CAPABILITY_TESTS = [
    {
        "id": "framework_comparison",
        "goal": "Research two Python web frameworks, compare performance tradeoffs, implement minimal example snippets, and recommend one for high-scale APIs.",
        "expected_agents": ["ResearchAgent", "CodingAgent", "SynthesizerAgent", "CriticAgent"],
        # supply deterministic plan to exercise routing
        "plan": [
            {
                "task_id": "t1",
                "title": "Framework Research",
                "instructions": "Research Python web frameworks and compare performance tradeoffs.",
                "depends_on": [],
            },
            {
                "task_id": "t2",
                "title": "Example Code",
                "instructions": "Write a minimal example snippet for a web API in one of the frameworks.",
                "depends_on": [],
            },
        ],
    },
    {
        "id": "data_pipeline_design",
        "goal": "Design a scalable data ingestion pipeline, provide architectural reasoning, and include a sample processing module.",
        "expected_agents": ["ResearchAgent", "CodingAgent", "SynthesizerAgent"],
        "plan": [
            {
                "task_id": "t1",
                "title": "Pipeline Research",
                "instructions": "Research scalable data ingestion patterns and architectures.",
                "depends_on": [],
            },
            {
                "task_id": "t2",
                "title": "Sample Module",
                "instructions": "Provide sample code for a processing module in the pipeline.",
                "depends_on": [],
            },
        ],
    },
    {
        "id": "conflicting_requirements",
        "goal": "Propose a system that is both fully decentralized and centrally controlled; explain tradeoffs and reconcile contradictions.",
        "expected_agents": ["ResearchAgent", "SynthesizerAgent", "CriticAgent"],
        "plan": [
            {
                "task_id": "t1",
                "title": "Decentralization vs Centralization",
                "instructions": "Research the tradeoffs between decentralization and central control.",
                "depends_on": [],
            },
            {
                "task_id": "t2",
                "title": "Reconciliation",
                "instructions": "Describe how a system could reconcile these conflicting requirements.",
                "depends_on": [],
            },
        ],
    },
    {
        "id": "memory_recall_test",
        "goal": "Based on previous framework research, summarize prior findings and refine the recommendation.",
        "expected_agents": ["SynthesizerAgent", "CriticAgent"],
        "requires_memory": True,
        "plan": [
            {
                "task_id": "t1",
                "title": "Memory Summary",
                "instructions": "Recall previous framework research from memory and summarize the key points.",
                "depends_on": [],
            },
        ],
    },
]
