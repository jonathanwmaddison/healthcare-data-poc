#!/usr/bin/env python3
"""
Multi-Agent Benchmark Runner for HDH-Bench

Uses official agent SDKs from each provider:
- OpenAI Agents SDK (Responses API)
- Google Agent Development Kit (ADK)
- Anthropic Claude Agent SDK

Usage:
    python scripts/run_agent_comparison.py --agents claude,openai,google
    python scripts/run_agent_comparison.py --tasks Q001,Q005
    python scripts/run_agent_comparison.py --all-tasks
"""

import argparse
import json
import os
import sys
import time
import asyncio
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod
import httpx

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

BENCHMARK_DIR = Path(__file__).parent.parent / "data" / "benchmark"
RESULTS_DIR = Path(__file__).parent.parent / "results"


@dataclass
class AgentResult:
    agent_name: str
    task_id: str
    response: Dict[str, Any]
    turns_used: int
    time_seconds: float
    tokens_used: int
    error: Optional[str] = None


def load_benchmark_context() -> tuple:
    """Load the agent prompt and API catalog."""
    prompt_path = BENCHMARK_DIR / "agent_prompt.md"
    catalog_path = BENCHMARK_DIR / "api_catalog.json"
    queries_path = BENCHMARK_DIR / "benchmark_queries.json"

    with open(prompt_path) as f:
        prompt = f.read()
    with open(catalog_path) as f:
        catalog = json.load(f)
    with open(queries_path) as f:
        queries = json.load(f)

    return prompt, catalog, queries


# ============================================================================
# FHIR Tool - Shared across all agents
# ============================================================================

def fhir_request(url: str) -> str:
    """Make a GET request to a FHIR API endpoint."""
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url)
            response.raise_for_status()
            result = response.json()
            return json.dumps(result)[:15000]
    except Exception as e:
        return json.dumps({"error": str(e)})


def _parse_json_response(text: str) -> Dict:
    """Extract JSON from agent text response."""
    import re
    if not text:
        return {}
    # Try raw parse first
    try:
        return json.loads(text.strip())
    except:
        pass
    # Try markdown code block
    match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', text)
    if match:
        try:
            return json.loads(match.group(1))
        except:
            pass
    # Try finding outermost JSON object
    match = re.search(r'(\{[\s\S]*\})', text)
    if match:
        try:
            return json.loads(match.group(1))
        except:
            pass
    return {"raw": text[:1000]}


FHIR_TOOL_DESCRIPTION = """Make a GET request to a FHIR R4 API endpoint.

Available systems:
- EHR (localhost:8001): Patient, Condition
- LIS (localhost:8002): Patient, ServiceRequest, Observation
- Pharmacy (localhost:8005): Patient, MedicationRequest
- PAS (localhost:8006): Patient, Encounter
- Billing (localhost:8007): Patient, Claim, Coverage

Search tips:
- Use _count and _offset for pagination: ?_count=50&_offset=0
- Condition code search needs EXACT codes: ?code=E11.9 (not E11)
- MedicationRequest does NOT support code search; fetch all with ?_count=200 and filter client-side
- Observation supports code search: ?code=4548-4
- To match patients across systems, search by name: ?name=Smith
- Check /fhir/r4/metadata for supported search parameters

Example URLs:
- http://localhost:8001/fhir/r4/Patient?_count=50
- http://localhost:8001/fhir/r4/Condition?code=E11.9
- http://localhost:8002/fhir/r4/Observation?code=4548-4
- http://localhost:8005/fhir/r4/MedicationRequest?_count=200
"""


# ============================================================================
# OpenAI Agents SDK (Codex/Agents framework)
# ============================================================================

class OpenAIAgentRunner:
    """OpenAI Agents SDK - the official agent framework from OpenAI."""

    def __init__(self):
        self.name = "OpenAI-Agents-SDK"
        self.api_key = os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not set")

    async def run_task(self, task: Dict, context: str) -> AgentResult:
        from agents import Agent, Runner, function_tool

        start_time = time.time()

        # Define FHIR tool using Agents SDK decorator
        @function_tool
        def fhir_api(url: str) -> str:
            """Make a GET request to a FHIR R4 API endpoint.

            Available systems:
            - EHR (localhost:8001): Patient, Condition
            - LIS (localhost:8002): Patient, ServiceRequest, Observation
            - Pharmacy (localhost:8005): Patient, MedicationRequest
            - PAS (localhost:8006): Patient, Encounter
            - Billing (localhost:8007): Patient, Claim, Coverage

            Search tips:
            - Use _count=200 and _offset for pagination
            - Condition code search needs EXACT codes: ?code=E11.9
            - MedicationRequest does NOT support code search; fetch all and filter
            - Match patients across systems by name: ?name=Smith

            Args:
                url: The full FHIR API URL (e.g. http://localhost:8001/fhir/r4/Patient)
            """
            return fhir_request(url)

        response_format = json.dumps(task.get('response_format', {}), indent=2)
        task_instructions = f"""{context[:6000]}

You are a healthcare data integration agent. Query FHIR APIs to complete tasks.
- Use _count=200 to get large result sets and _offset for pagination
- Patient IDs differ across systems. Match by name and DOB.
- If code search returns 0, fetch all with _count=200 and filter the JSON.
- Return your FINAL answer as a JSON object, no markdown wrapping.
"""

        task_prompt = f"""Complete this task:

**Task ID**: {task['id']}
**Title**: {task['title']}
**Description**: {task['description']}

Return your answer as JSON with these fields:
{response_format}
"""

        # Create agent
        agent = Agent(
            name="HDH-Bench-Agent",
            instructions=task_instructions,
            model="gpt-5.2",
            tools=[fhir_api],
        )

        # Run the agent loop
        result = await Runner.run(agent, task_prompt)

        elapsed = time.time() - start_time

        # Parse final output
        final_response = _parse_json_response(result.final_output)

        return AgentResult(
            agent_name=self.name,
            task_id=task['id'],
            response=final_response,
            turns_used=0,  # Runner doesn't expose turn count directly
            time_seconds=elapsed,
            tokens_used=0
        )


# ============================================================================
# Google Agent Development Kit (ADK)
# ============================================================================

class GoogleADKRunner:
    """Google Agent Development Kit."""

    def __init__(self):
        self.name = "Google-ADK"
        self.api_key = os.environ.get("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not set")

    async def run_task(self, task: Dict, context: str) -> AgentResult:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=self.api_key)
        start_time = time.time()
        turns = 0

        task_prompt = f"""
{context}

## Your Task

**Task ID**: {task['id']}
**Title**: {task['title']}
**Description**: {task['description']}

Use the fhir_request function to query healthcare APIs.
Return your final answer as valid JSON.
"""

        # Define FHIR tool for ADK
        fhir_tool = types.FunctionDeclaration(
            name="fhir_request",
            description=FHIR_TOOL_DESCRIPTION,
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "url": types.Schema(
                        type=types.Type.STRING,
                        description="The full FHIR API URL"
                    )
                },
                required=["url"]
            )
        )

        tools = types.Tool(function_declarations=[fhir_tool])

        # Create chat with tools
        chat = client.chats.create(
            model="gemini-2.0-flash",
            config=types.GenerateContentConfig(
                tools=[tools],
                temperature=0.1
            )
        )

        response = chat.send_message(task_prompt)
        max_turns = task.get("max_turns", 20)
        final_response = {}

        while turns < max_turns:
            turns += 1

            # Check for function calls
            has_function_call = False
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'function_call') and part.function_call:
                    has_function_call = True
                    fc = part.function_call
                    url = fc.args.get("url", "")
                    result = fhir_request(url)

                    # Send function response
                    response = chat.send_message(
                        types.Content(
                            parts=[types.Part(
                                function_response=types.FunctionResponse(
                                    name="fhir_request",
                                    response={"result": result}
                                )
                            )]
                        )
                    )
                    break

            if not has_function_call:
                # Extract final text response
                text = response.text if hasattr(response, 'text') else ""
                try:
                    import re
                    json_match = re.search(r'\{[\s\S]*\}', text)
                    if json_match:
                        final_response = json.loads(json_match.group())
                except:
                    final_response = {"raw_response": text[:1000]}
                break

        elapsed = time.time() - start_time

        return AgentResult(
            agent_name=self.name,
            task_id=task['id'],
            response=final_response,
            turns_used=turns,
            time_seconds=elapsed,
            tokens_used=0  # ADK doesn't expose token counts easily
        )


# ============================================================================
# Anthropic Claude Agent SDK
# ============================================================================

class ClaudeAgentRunner:
    """Anthropic Claude Agent SDK."""

    def __init__(self):
        self.name = "Claude-Agent-SDK"
        self.api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")

    async def run_task(self, task: Dict, context: str) -> AgentResult:
        from claude_agent_sdk import Agent, tool

        start_time = time.time()
        turns = 0

        # Define FHIR tool using Claude Agent SDK decorator
        @tool
        def fhir_request_tool(url: str) -> str:
            """Make a GET request to a FHIR R4 API endpoint.

            Args:
                url: The full FHIR API URL (e.g., http://localhost:8001/fhir/r4/Patient)

            Returns:
                JSON response from the FHIR API
            """
            return fhir_request(url)

        task_prompt = f"""
{context}

## Your Task

**Task ID**: {task['id']}
**Title**: {task['title']}
**Description**: {task['description']}

Use the fhir_request_tool to query the healthcare FHIR APIs.
Return your final answer as valid JSON matching the response_format.
"""

        # Create agent with custom tool
        agent = Agent(
            model="claude-sonnet-4-20250514",
            api_key=self.api_key,
            tools=[fhir_request_tool],
            max_turns=task.get("max_turns", 20)
        )

        # Run the agent
        result = await agent.run(task_prompt)

        elapsed = time.time() - start_time

        # Parse response
        final_response = {}
        if result.output:
            try:
                import re
                json_match = re.search(r'\{[\s\S]*\}', result.output)
                if json_match:
                    final_response = json.loads(json_match.group())
            except:
                final_response = {"raw_response": result.output[:1000]}

        return AgentResult(
            agent_name=self.name,
            task_id=task['id'],
            response=final_response,
            turns_used=result.turns_used if hasattr(result, 'turns_used') else 0,
            time_seconds=elapsed,
            tokens_used=result.tokens_used if hasattr(result, 'tokens_used') else 0
        )


# ============================================================================
# Fallback: Direct API Agent (no SDK dependencies)
# ============================================================================

class DirectAPIAgent:
    """Fallback agent using direct API calls (works without SDKs)."""

    def __init__(self, provider: str):
        self.provider = provider
        if provider == "openai":
            self.name = "OpenAI-Direct"
            self.api_key = os.environ.get("OPENAI_API_KEY")
            self.base_url = "https://api.openai.com/v1"
            self.model = "gpt-4o"
        elif provider == "anthropic":
            self.name = "Claude-Direct"
            self.api_key = os.environ.get("ANTHROPIC_API_KEY")
            self.base_url = "https://api.anthropic.com"
            self.model = "claude-opus-4-5-20251101"
        elif provider == "google":
            self.name = "Gemini-Direct"
            self.api_key = os.environ.get("GOOGLE_API_KEY")
            self.base_url = "https://generativelanguage.googleapis.com/v1beta"
            self.model = "gemini-2.0-flash"
        else:
            raise ValueError(f"Unknown provider: {provider}")

        if not self.api_key:
            raise ValueError(f"API key not set for {provider}")

    async def run_task(self, task: Dict, context: str) -> AgentResult:
        """Run task using direct API calls with tool use."""
        start_time = time.time()
        turns = 0
        total_tokens = 0
        max_turns = task.get("max_turns", 20)

        response_format = json.dumps(task.get('response_format', {}), indent=2)
        task_prompt = f"""
{context[:6000]}

## Your Task
**Task ID**: {task['id']}
**Title**: {task['title']}
**Description**: {task['description']}

## Required Response Format
Return your answer as a JSON object with EXACTLY these fields:
```json
{response_format}
```

Use the fhir_request tool to query the FHIR APIs. Return ONLY the final JSON object, no markdown.
"""

        if self.provider == "openai":
            return await self._run_openai(task, task_prompt, max_turns)
        elif self.provider == "anthropic":
            return await self._run_anthropic(task, task_prompt, max_turns)
        elif self.provider == "google":
            return await self._run_google(task, task_prompt, max_turns)

    async def _run_openai(self, task: Dict, prompt: str, max_turns: int) -> AgentResult:
        """OpenAI with function calling."""
        import openai
        client = openai.OpenAI(api_key=self.api_key)

        start_time = time.time()
        turns = 0
        total_tokens = 0

        messages = [
            {"role": "system", "content": """You are a healthcare data integration agent. Query FHIR APIs using the fhir_request tool.

Key strategies:
1. Use _count=200 to get large result sets. Use _offset for pagination if needed.
2. Patient IDs differ across systems (MRN-X, LAB-X, RX-X). Match patients by name/DOB.
3. Some search params may not be supported. If code search returns 0, try fetching all resources with _count=200 and filter the JSON yourself.
4. For Conditions, use exact ICD-10 codes (e.g. code=E11.9, not code=E11).
5. Return your FINAL answer as a JSON object (no markdown wrapping).
"""},
            {"role": "user", "content": prompt}
        ]
        tools = [{
            "type": "function",
            "function": {
                "name": "fhir_request",
                "description": FHIR_TOOL_DESCRIPTION,
                "parameters": {
                    "type": "object",
                    "properties": {"url": {"type": "string", "description": "Full FHIR API URL e.g. http://localhost:8001/fhir/r4/Patient"}},
                    "required": ["url"]
                }
            }
        }]

        final_response = {}

        while turns < max_turns:
            turns += 1
            try:
                response = client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto" if turns < max_turns - 1 else "none"
                )
            except Exception as e:
                print(f"\n      API error on turn {turns}: {e}")
                break

            total_tokens += response.usage.total_tokens if response.usage else 0
            message = response.choices[0].message
            finish = response.choices[0].finish_reason

            if message.tool_calls:
                messages.append(message)
                for tc in message.tool_calls:
                    args = json.loads(tc.function.arguments)
                    url = args.get("url", "")
                    print(f"\n      [Turn {turns}] GET {url[:80]}", end="", flush=True)
                    result = fhir_request(url)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result
                    })
            else:
                text = message.content or ""
                final_response = _parse_json_response(text)
                break

        return AgentResult(
            agent_name=self.name, task_id=task['id'],
            response=final_response, turns_used=turns,
            time_seconds=time.time() - start_time,
            tokens_used=total_tokens
        )

    async def _run_anthropic(self, task: Dict, prompt: str, max_turns: int) -> AgentResult:
        """Anthropic with tool use."""
        import anthropic
        client = anthropic.Anthropic(api_key=self.api_key)

        start_time = time.time()
        turns = 0
        total_tokens = 0

        messages = [{"role": "user", "content": prompt}]
        tools = [{
            "name": "fhir_request",
            "description": FHIR_TOOL_DESCRIPTION,
            "input_schema": {
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"]
            }
        }]

        final_response = {}

        while turns < max_turns:
            turns += 1
            response = client.messages.create(
                model=self.model,
                max_tokens=4096,
                tools=tools,
                messages=messages
            )

            total_tokens += response.usage.input_tokens + response.usage.output_tokens

            if response.stop_reason == "tool_use":
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        result = fhir_request(block.input.get("url", ""))
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result
                        })
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})
            else:
                for block in response.content:
                    if hasattr(block, 'text'):
                        final_response = _parse_json_response(block.text)
                        if final_response and "raw" not in final_response:
                            break
                break

        return AgentResult(
            agent_name=self.name, task_id=task['id'],
            response=final_response, turns_used=turns,
            time_seconds=time.time() - start_time,
            tokens_used=total_tokens
        )

    async def _run_google(self, task: Dict, prompt: str, max_turns: int) -> AgentResult:
        """Google Gemini with function calling."""
        import google.generativeai as genai
        genai.configure(api_key=self.api_key)

        start_time = time.time()
        turns = 0

        fhir_fn = genai.protos.FunctionDeclaration(
            name="fhir_request",
            description=FHIR_TOOL_DESCRIPTION,
            parameters=genai.protos.Schema(
                type=genai.protos.Type.OBJECT,
                properties={"url": genai.protos.Schema(type=genai.protos.Type.STRING)},
                required=["url"]
            )
        )

        model = genai.GenerativeModel(
            self.model,
            tools=[genai.protos.Tool(function_declarations=[fhir_fn])]
        )

        chat = model.start_chat()
        response = chat.send_message(prompt)
        final_response = {}

        while turns < max_turns:
            turns += 1
            has_fc = False

            for part in response.parts:
                if hasattr(part, 'function_call') and part.function_call:
                    has_fc = True
                    url = part.function_call.args.get("url", "")
                    result = fhir_request(url)
                    response = chat.send_message(
                        genai.protos.Content(parts=[
                            genai.protos.Part(function_response=genai.protos.FunctionResponse(
                                name="fhir_request",
                                response={"result": result}
                            ))
                        ])
                    )
                    break

            if not has_fc:
                text = response.text if hasattr(response, 'text') else ""
                final_response = _parse_json_response(text)
                break

        return AgentResult(
            agent_name=self.name, task_id=task['id'],
            response=final_response, turns_used=turns,
            time_seconds=time.time() - start_time,
            tokens_used=0
        )


# ============================================================================
# Scoring
# ============================================================================

def score_result(result: AgentResult, task: Dict) -> Dict:
    """Score a single agent result."""
    response = result.response

    if result.error or "error" in response:
        return {"score": 0.0, "reason": "Error during execution"}

    if not response or response == {}:
        return {"score": 0.0, "reason": "Empty response"}

    # Check response format
    expected_format = task.get("response_format", {})
    matched = sum(1 for f in expected_format if f in response)
    total = len(expected_format) or 1

    format_score = matched / total
    content_score = 0.5 if response else 0.0

    return {
        "score": round((format_score * 0.6) + (content_score * 0.4), 3),
        "format_score": round(format_score, 3),
        "fields_matched": f"{matched}/{total}"
    }


# ============================================================================
# Main Runner
# ============================================================================

def get_agent(name: str):
    """Get agent instance by name."""
    if name == "codex":
        # OpenAI Agents SDK (Codex framework)
        return OpenAIAgentRunner()
    elif name == "openai":
        # OpenAI direct Chat Completions API
        return DirectAPIAgent("openai")
    elif name == "google":
        return DirectAPIAgent("google")
    elif name in ("claude", "anthropic"):
        return DirectAPIAgent("anthropic")
    else:
        raise ValueError(f"Unknown agent: {name}")


async def run_benchmark(agent_names: List[str], task_ids: List[str], verbose: bool = False):
    """Run the benchmark."""
    prompt, catalog, queries = load_benchmark_context()
    context = f"{prompt}\n\n## API Catalog\n```json\n{json.dumps(catalog, indent=2)[:4000]}\n```"

    all_tasks = queries.get("queries", [])
    tasks = [t for t in all_tasks if t["id"] in task_ids] if task_ids else all_tasks

    print(f"\n{'='*60}")
    print("HDH-BENCH MULTI-AGENT COMPARISON")
    print(f"{'='*60}")
    print(f"Agents: {', '.join(agent_names)}")
    print(f"Tasks: {', '.join(t['id'] for t in tasks)}")
    print(f"{'='*60}\n")

    # Initialize agents
    agents = {}
    for name in agent_names:
        try:
            agents[name] = get_agent(name)
            print(f"  [OK] {agents[name].name}")
        except ValueError as e:
            print(f"  [SKIP] {name}: {e}")

    if not agents:
        print("ERROR: No agents available. Set API keys:")
        print("  export ANTHROPIC_API_KEY=...")
        print("  export OPENAI_API_KEY=...")
        print("  export GOOGLE_API_KEY=...")
        sys.exit(1)

    print()

    # Run
    results = []
    scores = {n: {"total": 0, "count": 0, "results": []} for n in agents}

    for task in tasks:
        print(f"\n--- {task['id']}: {task['title']} ---")

        for agent_name, agent in agents.items():
            print(f"  {agent.name}...", end=" ", flush=True)
            try:
                result = await agent.run_task(task, context)
                task_score = score_result(result, task)

                results.append({
                    "agent": agent.name,
                    "task_id": task["id"],
                    "response": result.response,
                    "turns": result.turns_used,
                    "time_seconds": round(result.time_seconds, 2),
                    "tokens": result.tokens_used,
                    "score": task_score
                })

                scores[agent_name]["total"] += task_score["score"]
                scores[agent_name]["count"] += 1
                scores[agent_name]["results"].append({"task": task["id"], "score": task_score["score"]})

                print(f"Score: {task_score['score']:.2f} ({result.time_seconds:.1f}s, {result.turns_used} turns)")

                if verbose and result.response:
                    print(f"      Response: {json.dumps(result.response)[:150]}...")

            except Exception as e:
                print(f"ERROR: {e}")
                results.append({"agent": agent.name, "task_id": task["id"], "error": str(e)})

    # Final scores
    print(f"\n{'='*60}")
    print("FINAL SCORES")
    print(f"{'='*60}")

    final_scores = {}
    for name, data in scores.items():
        avg = data["total"] / data["count"] if data["count"] else 0
        final_scores[name] = {"average": round(avg, 3), "tasks": data["count"]}
        agent_display = agents[name].name if name in agents else name
        print(f"  {agent_display:25} | {avg:.1%} | {data['count']} tasks")

    print(f"{'='*60}\n")

    return {
        "timestamp": datetime.now().isoformat(),
        "agents": [a.name for a in agents.values()],
        "tasks": [t["id"] for t in tasks],
        "results": results,
        "scores": final_scores
    }


def main():
    parser = argparse.ArgumentParser(description="HDH-Bench Multi-Agent Comparison")
    parser.add_argument("--agents", "-a", default="claude,openai,google",
                        help="Agents: claude,openai,google")
    parser.add_argument("--tasks", "-t", default="Q001,Q002,Q005",
                        help="Task IDs (default: Q001,Q002,Q005)")
    parser.add_argument("--all-tasks", action="store_true")
    parser.add_argument("--output", "-o", default="agent_comparison.json")
    parser.add_argument("--verbose", "-v", action="store_true")

    args = parser.parse_args()

    agent_names = [a.strip() for a in args.agents.split(",")]
    task_ids = [] if args.all_tasks else [t.strip() for t in args.tasks.split(",")]

    result = asyncio.run(run_benchmark(agent_names, task_ids, args.verbose))

    RESULTS_DIR.mkdir(exist_ok=True)
    output_path = RESULTS_DIR / args.output
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)

    print(f"Results saved to: {output_path}")


if __name__ == "__main__":
    main()
