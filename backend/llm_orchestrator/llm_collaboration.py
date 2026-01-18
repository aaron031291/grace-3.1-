import logging
import difflib
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid
from collections import defaultdict
from .multi_llm_client import MultiLLMClient, TaskType, LLMModel
from llm_orchestrator.repo_access import RepositoryAccessLayer
from llm_orchestrator.hallucination_guard import HallucinationGuard

logger = logging.getLogger(__name__)


class CollaborationMode(Enum):
    """Types of collaboration between LLMs."""
    DEBATE = "debate"  # Multiple LLMs debate a topic
    CONSENSUS = "consensus"  # LLMs work to reach consensus
    DELEGATION = "delegation"  # One LLM delegates to specialists
    REVIEW = "review"  # One LLM reviews another's output
    BRAINSTORM = "brainstorm"  # Multiple LLMs generate ideas
    VALIDATION = "validation"  # Multiple LLMs validate a result


class CollaborationRole(Enum):
    """Roles LLMs can play in collaboration."""
    COORDINATOR = "coordinator"  # Coordinates the collaboration
    SPECIALIST = "specialist"  # Domain specialist
    CRITIC = "critic"  # Critical reviewer
    VALIDATOR = "validator"  # Validates outputs
    GENERATOR = "generator"  # Generates ideas/solutions
    SYNTHESIZER = "synthesizer"  # Synthesizes multiple outputs


@dataclass
class CollaborationAgent:
    """An LLM agent participating in collaboration."""
    agent_id: str
    model: LLMModel
    role: CollaborationRole
    task_type: TaskType
    system_prompt: str
    context: Dict[str, Any]


@dataclass
class CollaborationMessage:
    """A message in LLM collaboration."""
    message_id: str
    from_agent_id: str
    to_agent_id: Optional[str]  # None = broadcast
    content: str
    message_type: str  # proposal, critique, question, answer, vote
    timestamp: datetime
    metadata: Dict[str, Any]


@dataclass
class CollaborationSession:
    """A collaboration session between multiple LLMs."""
    session_id: str
    mode: CollaborationMode
    topic: str
    agents: List[CollaborationAgent]
    messages: List[CollaborationMessage]
    consensus_reached: bool
    final_output: Optional[str]
    trust_score: float
    confidence_score: float
    genesis_key_id: Optional[str]
    started_at: datetime
    completed_at: Optional[datetime]


@dataclass
class DebateResult:
    """Result of an LLM debate."""
    winning_position: str
    vote_counts: Dict[str, int]
    arguments: List[Dict[str, Any]]
    synthesis: str
    confidence: float


@dataclass
class ConsensusResult:
    """Result of consensus building."""
    consensus_reached: bool
    consensus_content: str
    agreement_level: float
    holdouts: List[str]
    iterations: int


class LLMCollaborationHub:
    """
    Hub for inter-LLM collaboration.

    Coordinates multiple LLMs working together on complex tasks.
    """

    def __init__(
        self,
        multi_llm_client: Optional[MultiLLMClient] = None,
        repo_access: Optional[RepositoryAccessLayer] = None,
        hallucination_guard: Optional[HallucinationGuard] = None
    ):
        """
        Initialize collaboration hub.

        Args:
            multi_llm_client: Multi-LLM client
            repo_access: Repository access layer
            hallucination_guard: Hallucination guard
        """
        self.multi_llm = multi_llm_client
        self.repo_access = repo_access
        self.hallucination_guard = hallucination_guard

        # Active collaboration sessions
        self.active_sessions: Dict[str, CollaborationSession] = {}
        self.completed_sessions: List[CollaborationSession] = []

    # =======================================================================
    # COLLABORATION MODE: DEBATE
    # =======================================================================

    def start_debate(
        self,
        topic: str,
        positions: List[str],
        num_agents: int = 3,
        max_rounds: int = 3,
        user_id: Optional[str] = None
    ) -> DebateResult:
        """
        Start a debate between multiple LLMs.

        Args:
            topic: Debate topic
            positions: List of positions to argue (e.g., ["pro", "con", "neutral"])
            num_agents: Number of agents per position
            max_rounds: Maximum debate rounds
            user_id: User ID for tracking

        Returns:
            DebateResult with winning position and synthesis
        """
        logger.info(f"[DEBATE] Starting debate on: {topic}")

        session_id = f"debate_{uuid.uuid4().hex[:8]}"

        # Create agents for each position
        agents = []
        for position in positions:
            for i in range(num_agents):
                agent_id = f"agent_{position}_{i}"

                # Select model for debate
                model = self.multi_llm.select_model(
                    task_type=TaskType.REASONING,
                    prefer_speed=False
                )

                system_prompt = f"""You are participating in a structured debate on: {topic}

Your position: {position}

Your role:
1. Present clear, logical arguments supporting your position
2. Address counter-arguments respectfully
3. Use evidence and reasoning
4. Stay focused on the topic
5. Be willing to concede valid points

Debate guidelines:
- Be intellectually honest
- Use evidence when available
- Acknowledge limitations
- Focus on substance, not rhetoric
"""

                agent = CollaborationAgent(
                    agent_id=agent_id,
                    model=model,
                    role=CollaborationRole.SPECIALIST,
                    task_type=TaskType.REASONING,
                    system_prompt=system_prompt,
                    context={"position": position, "topic": topic}
                )
                agents.append(agent)

        # Create session
        session = CollaborationSession(
            session_id=session_id,
            mode=CollaborationMode.DEBATE,
            topic=topic,
            agents=agents,
            messages=[],
            consensus_reached=False,
            final_output=None,
            trust_score=0.0,
            confidence_score=0.0,
            genesis_key_id=None,
            started_at=datetime.now(),
            completed_at=None
        )
        self.active_sessions[session_id] = session

        # Run debate rounds
        all_arguments = []

        for round_num in range(max_rounds):
            logger.info(f"[DEBATE] Round {round_num + 1}/{max_rounds}")

            for agent in agents:
                # Build context from previous arguments
                context = self._build_debate_context(session, agent.context["position"])

                prompt = f"""Debate Topic: {topic}
Your Position: {agent.context['position']}

Round {round_num + 1}:

{context}

Present your argument or response (keep it concise, 2-3 paragraphs):"""

                # Generate argument
                response = self.multi_llm.generate(
                    prompt=prompt,
                    task_type=TaskType.REASONING,
                    model_id=agent.model.model_id,
                    system_prompt=agent.system_prompt,
                    temperature=0.7
                )

                if response["success"]:
                    # Record message
                    message = CollaborationMessage(
                        message_id=f"msg_{uuid.uuid4().hex[:8]}",
                        from_agent_id=agent.agent_id,
                        to_agent_id=None,  # Broadcast
                        content=response["content"],
                        message_type="argument",
                        timestamp=datetime.now(),
                        metadata={
                            "round": round_num + 1,
                            "position": agent.context["position"]
                        }
                    )
                    session.messages.append(message)

                    all_arguments.append({
                        "agent_id": agent.agent_id,
                        "position": agent.context["position"],
                        "round": round_num + 1,
                        "argument": response["content"]
                    })

        # Vote on winning position
        vote_counts = self._conduct_vote(session, positions)

        # Generate synthesis
        synthesis = self._synthesize_debate(session, all_arguments)

        # Calculate confidence
        total_votes = sum(vote_counts.values())
        max_votes = max(vote_counts.values())
        confidence = max_votes / total_votes if total_votes > 0 else 0.0

        winning_position = max(vote_counts, key=vote_counts.get)

        session.consensus_reached = True
        session.final_output = synthesis
        session.confidence_score = confidence
        session.completed_at = datetime.now()

        # Move to completed
        self.completed_sessions.append(session)
        del self.active_sessions[session_id]

        result = DebateResult(
            winning_position=winning_position,
            vote_counts=vote_counts,
            arguments=all_arguments,
            synthesis=synthesis,
            confidence=confidence
        )

        logger.info(f"[DEBATE] Completed. Winner: {winning_position} ({confidence:.2%} confidence)")

        return result

    def _build_debate_context(self, session: CollaborationSession, position: str) -> str:
        """Build context from previous debate messages."""
        context_lines = []

        for msg in session.messages[-6:]:  # Last 6 messages
            msg_position = msg.metadata.get("position", "unknown")
            context_lines.append(f"{msg_position.upper()}: {msg.content[:200]}...")

        return "\n\n".join(context_lines) if context_lines else "No previous arguments yet."

    def _conduct_vote(self, session: CollaborationSession, positions: List[str]) -> Dict[str, int]:
        """Conduct vote on debate positions."""
        vote_counts = {pos: 0 for pos in positions}

        # Create neutral judge agent
        judge_model = self.multi_llm.select_model(
            task_type=TaskType.REASONING,
            prefer_speed=False
        )

        # Prepare debate summary
        debate_summary = self._summarize_debate(session)

        prompt = f"""You are an impartial judge evaluating a debate.

Topic: {session.topic}
Positions: {', '.join(positions)}

Debate Summary:
{debate_summary}

Based on the quality of arguments, logic, and evidence presented, which position had the strongest case?

Respond with ONLY the position name: {' or '.join(positions)}"""

        response = self.multi_llm.generate(
            prompt=prompt,
            task_type=TaskType.REASONING,
            model_id=judge_model.model_id,
            temperature=0.3  # Low temperature for objective judgment
        )

        if response["success"]:
            vote = response["content"].strip().lower()
            for position in positions:
                if position.lower() in vote:
                    vote_counts[position] += 1
                    break

        return vote_counts

    def _summarize_debate(self, session: CollaborationSession) -> str:
        """Summarize debate messages."""
        summary_lines = []
        for msg in session.messages:
            position = msg.metadata.get("position", "unknown")
            summary_lines.append(f"{position.upper()}: {msg.content[:300]}...")
        return "\n\n".join(summary_lines[:10])  # Last 10 messages

    def _synthesize_debate(self, session: CollaborationSession, arguments: List[Dict]) -> str:
        """Synthesize debate into final summary."""
        synthesizer_model = self.multi_llm.select_model(
            task_type=TaskType.REASONING,
            prefer_speed=False
        )

        debate_summary = self._summarize_debate(session)

        prompt = f"""Synthesize this debate into a balanced summary.

Topic: {session.topic}

Debate:
{debate_summary}

Provide a synthesis that:
1. Summarizes key arguments from all positions
2. Identifies areas of agreement
3. Acknowledges valid points from each side
4. Provides a balanced conclusion

Synthesis:"""

        response = self.multi_llm.generate(
            prompt=prompt,
            task_type=TaskType.REASONING,
            model_id=synthesizer_model.model_id,
            system_prompt="You are an expert at synthesizing complex debates into balanced summaries.",
            temperature=0.5
        )

        return response.get("content", "Unable to generate synthesis") if response["success"] else "Synthesis failed"

    # =======================================================================
    # COLLABORATION MODE: CONSENSUS
    # =======================================================================

    def build_consensus(
        self,
        topic: str,
        initial_proposals: List[str],
        num_agents: int = 5,
        max_iterations: int = 5,
        agreement_threshold: float = 0.8
    ) -> ConsensusResult:
        """
        Build consensus among multiple LLMs.

        Args:
            topic: Topic to reach consensus on
            initial_proposals: Initial proposals to consider
            num_agents: Number of agents
            max_iterations: Maximum consensus iterations
            agreement_threshold: Required agreement level (0.0-1.0)

        Returns:
            ConsensusResult with consensus content and agreement level
        """
        logger.info(f"[CONSENSUS] Building consensus on: {topic}")

        session_id = f"consensus_{uuid.uuid4().hex[:8]}"

        # Create agents
        agents = []
        for i in range(num_agents):
            agent_id = f"agent_consensus_{i}"

            model = self.multi_llm.select_model(
                task_type=TaskType.REASONING,
                prefer_speed=False
            )

            system_prompt = """You are participating in a consensus-building process.

Your role:
1. Evaluate proposals carefully
2. Identify strengths and weaknesses
3. Suggest improvements
4. Be willing to compromise
5. Focus on finding common ground

Guidelines:
- Be constructive and collaborative
- Acknowledge good ideas from others
- Propose concrete improvements
- Signal when you agree/disagree
"""

            agent = CollaborationAgent(
                agent_id=agent_id,
                model=model,
                role=CollaborationRole.VALIDATOR,
                task_type=TaskType.REASONING,
                system_prompt=system_prompt,
                context={"topic": topic}
            )
            agents.append(agent)

        # Create session
        session = CollaborationSession(
            session_id=session_id,
            mode=CollaborationMode.CONSENSUS,
            topic=topic,
            agents=agents,
            messages=[],
            consensus_reached=False,
            final_output=None,
            trust_score=0.0,
            confidence_score=0.0,
            genesis_key_id=None,
            started_at=datetime.now(),
            completed_at=None
        )
        self.active_sessions[session_id] = session

        # Iterative consensus building
        current_proposals = initial_proposals.copy()
        iteration = 0
        consensus_reached = False
        holdouts = []

        while iteration < max_iterations and not consensus_reached:
            iteration += 1
            logger.info(f"[CONSENSUS] Iteration {iteration}/{max_iterations}")

            # Get feedback from all agents
            feedback_list = []

            for agent in agents:
                prompt = f"""Topic: {topic}

Current Proposals:
{chr(10).join(f"{i+1}. {p}" for i, p in enumerate(current_proposals))}

Iteration {iteration}:

Your task:
1. Evaluate each proposal
2. Identify your preferred proposal (or suggest improvements)
3. Rate your agreement level (0-10)

Response format:
PREFERRED: [proposal number or "modified"]
AGREEMENT: [0-10]
FEEDBACK: [your feedback]
IMPROVED: [improved version if you suggest changes]"""

                response = self.multi_llm.generate(
                    prompt=prompt,
                    task_type=TaskType.REASONING,
                    model_id=agent.model.model_id,
                    system_prompt=agent.system_prompt,
                    temperature=0.6
                )

                if response["success"]:
                    feedback_list.append({
                        "agent_id": agent.agent_id,
                        "feedback": response["content"]
                    })

                    # Record message
                    message = CollaborationMessage(
                        message_id=f"msg_{uuid.uuid4().hex[:8]}",
                        from_agent_id=agent.agent_id,
                        to_agent_id=None,
                        content=response["content"],
                        message_type="feedback",
                        timestamp=datetime.now(),
                        metadata={"iteration": iteration}
                    )
                    session.messages.append(message)

            # Analyze agreement level
            agreement_level = self._analyze_agreement(feedback_list)

            if agreement_level >= agreement_threshold:
                consensus_reached = True
                logger.info(f"[CONSENSUS] Consensus reached! Agreement: {agreement_level:.2%}")
            else:
                # Generate improved proposals based on feedback
                current_proposals = self._merge_proposals(session, feedback_list, current_proposals)
                logger.info(f"[CONSENSUS] Agreement: {agreement_level:.2%}, continuing...")

        # Generate final consensus
        if consensus_reached:
            final_consensus = self._generate_final_consensus(session, current_proposals)
        else:
            final_consensus = current_proposals[0] if current_proposals else "No consensus reached"
            holdouts = [agent.agent_id for agent in agents]

        session.consensus_reached = consensus_reached
        session.final_output = final_consensus
        session.confidence_score = agreement_level if consensus_reached else 0.0
        session.completed_at = datetime.now()

        # Move to completed
        self.completed_sessions.append(session)
        del self.active_sessions[session_id]

        result = ConsensusResult(
            consensus_reached=consensus_reached,
            consensus_content=final_consensus,
            agreement_level=agreement_level,
            holdouts=holdouts,
            iterations=iteration
        )

        return result

    def _analyze_agreement(self, feedback_list: List[Dict]) -> float:
        """Analyze agreement level from feedback."""
        # Simple implementation: parse AGREEMENT scores
        scores = []
        for feedback in feedback_list:
            content = feedback["feedback"]
            # Try to extract agreement score
            if "AGREEMENT:" in content:
                try:
                    score_str = content.split("AGREEMENT:")[1].split("\n")[0].strip()
                    score = float(score_str.split()[0])
                    scores.append(score / 10.0)  # Normalize to 0-1
                except (ValueError, IndexError):
                    scores.append(0.5)  # Default neutral
            else:
                scores.append(0.5)

        return sum(scores) / len(scores) if scores else 0.0

    def _merge_proposals(
        self,
        session: CollaborationSession,
        feedback_list: List[Dict],
        current_proposals: List[str]
    ) -> List[str]:
        """Merge proposals based on feedback."""
        # Use synthesizer to merge proposals
        synthesizer_model = self.multi_llm.select_model(
            task_type=TaskType.REASONING,
            prefer_speed=False
        )

        feedback_text = "\n\n".join([f["feedback"] for f in feedback_list])

        prompt = f"""Topic: {session.topic}

Current Proposals:
{chr(10).join(f"{i+1}. {p}" for i, p in enumerate(current_proposals))}

Agent Feedback:
{feedback_text}

Task: Synthesize an improved proposal that addresses the feedback and finds common ground.

Improved Proposal:"""

        response = self.multi_llm.generate(
            prompt=prompt,
            task_type=TaskType.REASONING,
            model_id=synthesizer_model.model_id,
            temperature=0.6
        )

        if response["success"]:
            return [response["content"]]
        return current_proposals

    def _generate_final_consensus(self, session: CollaborationSession, proposals: List[str]) -> str:
        """Generate final consensus statement."""
        return proposals[0] if proposals else "Consensus reached (no specific proposal)"

    # =======================================================================
    # COLLABORATION MODE: DELEGATION
    # =======================================================================

    def delegate_task(
        self,
        task: str,
        task_type: TaskType,
        num_specialists: int = 3,
        coordinator_reviews: bool = True
    ) -> Dict[str, Any]:
        """
        Delegate task to specialized LLM agents.

        Args:
            task: Task description
            task_type: Type of task
            num_specialists: Number of specialist agents
            coordinator_reviews: Whether coordinator reviews results

        Returns:
            Delegation result with specialist outputs
        """
        logger.info(f"[DELEGATION] Delegating task: {task[:100]}...")

        session_id = f"delegation_{uuid.uuid4().hex[:8]}"

        # Create coordinator agent
        coordinator_model = self.multi_llm.select_model(
            task_type=TaskType.REASONING,
            prefer_speed=False
        )

        coordinator = CollaborationAgent(
            agent_id="coordinator",
            model=coordinator_model,
            role=CollaborationRole.COORDINATOR,
            task_type=TaskType.REASONING,
            system_prompt="You coordinate specialist agents and synthesize their outputs.",
            context={}
        )

        # Create specialist agents
        specialists = []
        for i in range(num_specialists):
            specialist_model = self.multi_llm.select_model(
                task_type=task_type,
                prefer_speed=False
            )

            specialist = CollaborationAgent(
                agent_id=f"specialist_{i}",
                model=specialist_model,
                role=CollaborationRole.SPECIALIST,
                task_type=task_type,
                system_prompt=f"You are a specialist in {task_type.value}. Provide expert analysis.",
                context={}
            )
            specialists.append(specialist)

        # Get specialist responses
        specialist_outputs = []

        for specialist in specialists:
            response = self.multi_llm.generate(
                prompt=task,
                task_type=task_type,
                model_id=specialist.model.model_id,
                system_prompt=specialist.system_prompt
            )

            if response["success"]:
                specialist_outputs.append({
                    "agent_id": specialist.agent_id,
                    "model": specialist.model.name,
                    "output": response["content"]
                })

        # Coordinator synthesis
        if coordinator_reviews:
            synthesis_prompt = f"""Task: {task}

Specialist Outputs:
{chr(10).join(f"{i+1}. {o['output'][:300]}..." for i, o in enumerate(specialist_outputs))}

Synthesize the specialist outputs into a coherent final result:"""

            synthesis_response = self.multi_llm.generate(
                prompt=synthesis_prompt,
                task_type=TaskType.REASONING,
                model_id=coordinator.model.model_id,
                system_prompt=coordinator.system_prompt
            )

            final_output = synthesis_response["content"] if synthesis_response["success"] else specialist_outputs[0]["output"]
        else:
            final_output = specialist_outputs[0]["output"]

        return {
            "task": task,
            "specialist_outputs": specialist_outputs,
            "final_output": final_output,
            "num_specialists": len(specialist_outputs)
        }

    # =======================================================================
    # COLLABORATION MODE: REVIEW
    # =======================================================================

    def peer_review(
        self,
        content: str,
        review_aspects: List[str],
        num_reviewers: int = 3
    ) -> Dict[str, Any]:
        """
        Have multiple LLMs review content.

        Args:
            content: Content to review
            review_aspects: Aspects to review (e.g., ["accuracy", "clarity", "completeness"])
            num_reviewers: Number of reviewer agents

        Returns:
            Review results with feedback and ratings
        """
        logger.info(f"[REVIEW] Starting peer review with {num_reviewers} reviewers")

        reviews = []

        for i in range(num_reviewers):
            reviewer_model = self.multi_llm.select_model(
                task_type=TaskType.REASONING,
                prefer_speed=False
            )

            prompt = f"""Review the following content:

{content}

Review Aspects:
{chr(10).join(f"- {aspect}" for aspect in review_aspects)}

For each aspect, provide:
1. Rating (0-10)
2. Feedback
3. Suggestions for improvement

Format:
ASPECT: [aspect name]
RATING: [0-10]
FEEDBACK: [your feedback]
SUGGESTIONS: [improvements]

---"""

            response = self.multi_llm.generate(
                prompt=prompt,
                task_type=TaskType.REASONING,
                model_id=reviewer_model.model_id,
                system_prompt="You are an expert reviewer. Provide constructive, detailed feedback.",
                temperature=0.6
            )

            if response["success"]:
                reviews.append({
                    "reviewer_id": f"reviewer_{i}",
                    "model": reviewer_model.name,
                    "review": response["content"]
                })

        # Aggregate ratings
        aggregate_ratings = self._aggregate_review_ratings(reviews, review_aspects)

        return {
            "reviews": reviews,
            "aggregate_ratings": aggregate_ratings,
            "num_reviewers": len(reviews)
        }

    def _aggregate_review_ratings(self, reviews: List[Dict], aspects: List[str]) -> Dict[str, float]:
        """Aggregate review ratings from parsed reviews."""
        aspect_scores: Dict[str, List[float]] = defaultdict(list)
        
        for review in reviews:
            content = review.get("review", "")
            for aspect in aspects:
                score = self._extract_aspect_score(content, aspect)
                if score is not None:
                    aspect_scores[aspect].append(score)
        
        aggregated = {}
        for aspect in aspects:
            scores = aspect_scores.get(aspect, [])
            if scores:
                aggregated[aspect] = sum(scores) / len(scores)
            else:
                aggregated[aspect] = 5.0  # Default neutral score
        
        return aggregated
    
    def _extract_aspect_score(self, content: str, aspect: str) -> Optional[float]:
        """Extract a numeric score for an aspect from review content."""
        content_lower = content.lower()
        aspect_lower = aspect.lower()
        
        patterns = [
            rf'{aspect_lower}\s*:\s*(\d+(?:\.\d+)?)\s*/\s*10',
            rf'{aspect_lower}\s*:\s*(\d+(?:\.\d+)?)',
            rf'{aspect_lower}\s+score\s*:\s*(\d+(?:\.\d+)?)',
            rf'{aspect_lower}\s*=\s*(\d+(?:\.\d+)?)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content_lower)
            if match:
                try:
                    score = float(match.group(1))
                    # Normalize to 0-10 scale if needed
                    if score > 10:
                        score = 10.0
                    return score
                except ValueError:
                    continue
        
        return None

    def calculate_consensus_scores(
        self,
        responses: List[Dict[str, Any]],
        similarity_threshold: float = 0.7
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive consensus scores from multiple LLM responses.
        
        Args:
            responses: List of response dicts with keys:
                - model: str (model name/id)
                - content: str (response content)
                - confidence: float (0.0-1.0, optional)
                - historical_accuracy: float (0.0-1.0, optional)
            similarity_threshold: Minimum similarity to group responses together
            
        Returns:
            Dict with consensus metrics:
                - consensus_score: Overall weighted consensus (0.0-1.0)
                - agreement_rate: Fraction of LLMs agreeing on winning response
                - winning_response: The consensus response content
                - vote_distribution: Votes per response group
                - participating_models: List of model names
                - individual_scores: Per-model breakdown
                - response_groups: Grouped similar responses
        """
        if not responses:
            return {
                "consensus_score": 0.0,
                "agreement_rate": 0.0,
                "winning_response": "",
                "vote_distribution": {},
                "participating_models": [],
                "individual_scores": {},
                "response_groups": []
            }
        
        # Extract response contents and metadata
        contents = []
        models = []
        confidences = []
        historical_accuracies = []
        
        for resp in responses:
            contents.append(resp.get("content", ""))
            models.append(resp.get("model", f"model_{len(models)}"))
            confidences.append(resp.get("confidence", 0.5))
            historical_accuracies.append(resp.get("historical_accuracy", 0.5))
        
        # Group similar responses using text similarity
        response_groups = self._group_similar_responses(
            contents, models, similarity_threshold
        )
        
        # Calculate weighted votes for each group
        vote_distribution = {}
        group_weighted_scores = {}
        
        for group_id, group in enumerate(response_groups):
            group_name = f"response_{group_id + 1}"
            vote_count = len(group["members"])
            vote_distribution[group_name] = vote_count
            
            # Calculate weighted score for this group
            weighted_score = 0.0
            for member_idx in group["member_indices"]:
                confidence_weight = confidences[member_idx]
                accuracy_weight = historical_accuracies[member_idx]
                # Combined weight: 60% confidence, 40% historical accuracy
                combined_weight = 0.6 * confidence_weight + 0.4 * accuracy_weight
                weighted_score += combined_weight
            
            group_weighted_scores[group_name] = weighted_score
        
        # Find winning response group
        if group_weighted_scores:
            winning_group_name = max(group_weighted_scores, key=group_weighted_scores.get)
            winning_group_idx = int(winning_group_name.split("_")[1]) - 1
            winning_response = response_groups[winning_group_idx]["representative"]
            winning_vote_count = vote_distribution[winning_group_name]
        else:
            winning_response = contents[0] if contents else ""
            winning_vote_count = 1
        
        # Calculate agreement rate
        total_responses = len(responses)
        agreement_rate = winning_vote_count / total_responses if total_responses > 0 else 0.0
        
        # Calculate overall consensus score
        # Combines: agreement rate, weighted confidence, response similarity within groups
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.5
        avg_accuracy = sum(historical_accuracies) / len(historical_accuracies) if historical_accuracies else 0.5
        
        # Intra-group similarity bonus
        intra_group_similarity = self._calculate_intra_group_similarity(response_groups)
        
        # Consensus score formula:
        # 40% agreement rate + 25% confidence + 20% historical accuracy + 15% similarity
        consensus_score = (
            0.40 * agreement_rate +
            0.25 * avg_confidence +
            0.20 * avg_accuracy +
            0.15 * intra_group_similarity
        )
        consensus_score = min(1.0, max(0.0, consensus_score))
        
        # Individual scores per model
        individual_scores = {}
        for i, model in enumerate(models):
            # Find which group this model belongs to
            model_group = None
            for g_idx, group in enumerate(response_groups):
                if i in group["member_indices"]:
                    model_group = f"response_{g_idx + 1}"
                    break
            
            individual_scores[model] = {
                "confidence": confidences[i],
                "historical_accuracy": historical_accuracies[i],
                "response_group": model_group,
                "agrees_with_consensus": model_group == winning_group_name if winning_group_name else False
            }
        
        return {
            "consensus_score": round(consensus_score, 4),
            "agreement_rate": round(agreement_rate, 4),
            "winning_response": winning_response,
            "vote_distribution": vote_distribution,
            "participating_models": models,
            "individual_scores": individual_scores,
            "response_groups": [
                {
                    "group_id": f"response_{i+1}",
                    "members": g["members"],
                    "representative": g["representative"][:200] + "..." if len(g["representative"]) > 200 else g["representative"],
                    "avg_similarity": g["avg_similarity"]
                }
                for i, g in enumerate(response_groups)
            ]
        }
    
    def _group_similar_responses(
        self,
        contents: List[str],
        models: List[str],
        threshold: float
    ) -> List[Dict[str, Any]]:
        """
        Group similar responses together using text similarity.
        
        Uses difflib.SequenceMatcher for text similarity comparison.
        """
        if not contents:
            return []
        
        n = len(contents)
        assigned = [False] * n
        groups = []
        
        for i in range(n):
            if assigned[i]:
                continue
            
            # Start new group with this response
            group = {
                "members": [models[i]],
                "member_indices": [i],
                "representative": contents[i],
                "similarities": []
            }
            assigned[i] = True
            
            # Find similar responses
            for j in range(i + 1, n):
                if assigned[j]:
                    continue
                
                similarity = self._calculate_text_similarity(contents[i], contents[j])
                
                if similarity >= threshold:
                    group["members"].append(models[j])
                    group["member_indices"].append(j)
                    group["similarities"].append(similarity)
                    assigned[j] = True
            
            # Calculate average similarity within group
            if group["similarities"]:
                group["avg_similarity"] = sum(group["similarities"]) / len(group["similarities"])
            else:
                group["avg_similarity"] = 1.0  # Single member = perfect self-similarity
            
            groups.append(group)
        
        return groups
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate similarity between two texts using difflib.
        
        Returns a float between 0.0 (no similarity) and 1.0 (identical).
        """
        if not text1 or not text2:
            return 0.0
        
        # Normalize texts
        text1_normalized = text1.lower().strip()
        text2_normalized = text2.lower().strip()
        
        # Use SequenceMatcher for similarity
        matcher = difflib.SequenceMatcher(None, text1_normalized, text2_normalized)
        return matcher.ratio()
    
    def _calculate_intra_group_similarity(self, groups: List[Dict[str, Any]]) -> float:
        """
        Calculate average intra-group similarity across all groups.
        
        Higher value means responses within groups are more similar.
        """
        if not groups:
            return 0.0
        
        total_similarity = 0.0
        total_weight = 0
        
        for group in groups:
            group_size = len(group["members"])
            # Weight by group size - larger groups matter more
            total_similarity += group["avg_similarity"] * group_size
            total_weight += group_size
        
        return total_similarity / total_weight if total_weight > 0 else 0.0

    # =======================================================================
    # UTILITY METHODS
    # =======================================================================

    def get_session(self, session_id: str) -> Optional[CollaborationSession]:
        """Get collaboration session by ID."""
        if session_id in self.active_sessions:
            return self.active_sessions[session_id]

        for session in self.completed_sessions:
            if session.session_id == session_id:
                return session

        return None

    def get_active_sessions(self) -> List[CollaborationSession]:
        """Get all active collaboration sessions."""
        return list(self.active_sessions.values())

    def get_collaboration_stats(self) -> Dict[str, Any]:
        """Get collaboration statistics."""
        return {
            "active_sessions": len(self.active_sessions),
            "completed_sessions": len(self.completed_sessions),
            "total_sessions": len(self.active_sessions) + len(self.completed_sessions),
            "by_mode": {
                mode.value: sum(1 for s in self.completed_sessions if s.mode == mode)
                for mode in CollaborationMode
            }
        }


# Global instance
_collaboration_hub: Optional[LLMCollaborationHub] = None


def get_collaboration_hub(
    multi_llm_client: Optional[MultiLLMClient] = None,
    repo_access: Optional[RepositoryAccessLayer] = None,
    hallucination_guard: Optional[HallucinationGuard] = None
) -> LLMCollaborationHub:
    """Get or create global collaboration hub instance."""
    global _collaboration_hub
    if _collaboration_hub is None:
        _collaboration_hub = LLMCollaborationHub(
            multi_llm_client=multi_llm_client,
            repo_access=repo_access,
            hallucination_guard=hallucination_guard
        )
    return _collaboration_hub
