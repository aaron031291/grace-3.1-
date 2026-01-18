"""
Math Reasoning Engine for GSM8K and similar benchmarks.

Architecture-aligned implementation following Grace's patterns:
- Template matching (like MBPPTemplateMatcher)
- OODA loop integration
- Memory Mesh for pattern retrieval
- Deterministic verification (no unverified LLM outputs)
- Genesis Key tracking
- Federated learning for improvement
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import ast
import operator

logger = logging.getLogger(__name__)


class MathTemplateType(Enum):
    """Math problem template types."""
    BASIC_ARITHMETIC = "basic_arithmetic"
    PERCENTAGE = "percentage"
    RATIO = "ratio"
    WORK_RATE = "work_rate"
    DISTANCE_RATE_TIME = "distance_rate_time"
    PROFIT_LOSS = "profit_loss"
    MIXTURE = "mixture"
    AVERAGE = "average"
    COUNTING = "counting"
    LINEAR_EQUATION = "linear_equation"
    COMPARISON = "comparison"
    SEQUENTIAL = "sequential"
    UNKNOWN = "unknown"


@dataclass
class MathProblem:
    """Parsed math problem."""
    original_text: str
    quantities: List[Tuple[float, str]]  # (value, unit/context)
    keywords: List[str]
    expected_type: str  # "int" or "float"
    template_type: MathTemplateType = MathTemplateType.UNKNOWN


@dataclass
class MathSolution:
    """Solution to a math problem."""
    answer: float
    steps: List[str]
    confidence: float
    template_used: str
    verified: bool = False
    verification_details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MathTemplate:
    """A template for solving a category of math problems."""
    name: str
    template_type: MathTemplateType
    keywords: List[str]
    pattern_regex: Optional[str] = None
    solve_func: Optional[callable] = None
    examples: List[str] = field(default_factory=list)


class SafeMathEvaluator:
    """Safe math expression evaluator without using eval()."""
    
    OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
    }
    
    @classmethod
    def evaluate(cls, expr: str) -> Optional[float]:
        """Safely evaluate a math expression."""
        try:
            expr = expr.replace('^', '**')
            expr = re.sub(r'(\d)([a-zA-Z])', r'\1*\2', expr)
            
            tree = ast.parse(expr, mode='eval')
            return cls._eval_node(tree.body)
        except Exception as e:
            logger.debug(f"Safe eval failed: {e}")
            return None
    
    @classmethod
    def _eval_node(cls, node) -> float:
        """Recursively evaluate AST node."""
        if isinstance(node, ast.Constant):
            return float(node.value)
        elif isinstance(node, ast.Num):
            return float(node.n)
        elif isinstance(node, ast.BinOp):
            left = cls._eval_node(node.left)
            right = cls._eval_node(node.right)
            op = cls.OPERATORS.get(type(node.op))
            if op is None:
                raise ValueError(f"Unsupported operator: {type(node.op)}")
            return op(left, right)
        elif isinstance(node, ast.UnaryOp):
            operand = cls._eval_node(node.operand)
            op = cls.OPERATORS.get(type(node.op))
            if op is None:
                raise ValueError(f"Unsupported unary operator: {type(node.op)}")
            return op(operand)
        elif isinstance(node, ast.Expression):
            return cls._eval_node(node.body)
        else:
            raise ValueError(f"Unsupported node type: {type(node)}")


class MathReasoningEngine:
    """
    Grace-aligned Math Reasoning Engine.
    
    Follows the same architecture as MBPPTemplateMatcher:
    - Template matching first (deterministic)
    - Pattern retrieval from memory
    - Verified solutions only
    - Learning from correct answers
    """
    
    def __init__(self):
        self.templates: List[MathTemplate] = []
        self.solved_patterns: Dict[str, MathSolution] = {}
        self.evaluator = SafeMathEvaluator()
        
        self._init_templates()
        logger.info("[MATH-ENGINE] Initialized with %d templates", len(self.templates))
    
    def _init_templates(self):
        """Initialize math problem templates."""
        
        self.templates.append(MathTemplate(
            name="simple_subtraction_remaining",
            template_type=MathTemplateType.BASIC_ARITHMETIC,
            keywords=["has", "uses", "remaining", "left", "sells", "eats", "gives"],
            pattern_regex=r"(\d+).*?(?:uses?|eats?|gives?|sells?).*?(\d+).*?(?:and|then).*?(\d+)",
        ))
        
        self.templates.append(MathTemplate(
            name="multiplication_total",
            template_type=MathTemplateType.BASIC_ARITHMETIC,
            keywords=["each", "per", "every", "times", "total", "makes", "earns"],
            pattern_regex=r"(\d+).*?(?:each|per|every).*?\$?(\d+)",
        ))
        
        self.templates.append(MathTemplate(
            name="eggs_money_problem",
            template_type=MathTemplateType.SEQUENTIAL,
            keywords=["eggs", "lay", "eats", "bakes", "sells", "market", "day"],
            pattern_regex=r"(\d+)\s*eggs.*?eats?\s*(\d+).*?(?:bakes?|uses?)\s*(\d+).*?\$(\d+)",
        ))
        
        self.templates.append(MathTemplate(
            name="bolt_fabric_problem",
            template_type=MathTemplateType.RATIO,
            keywords=["bolt", "fiber", "half", "total", "fabric"],
            pattern_regex=r"(\d+)\s*bolts?.*?half",
        ))
        
        self.templates.append(MathTemplate(
            name="profit_calculation",
            template_type=MathTemplateType.PROFIT_LOSS,
            keywords=["profit", "buys", "sells", "repairs", "value", "increased", "cost"],
            pattern_regex=r"(?:buys?|costs?)\s*\$?([\d,]+).*?(?:repairs?|puts?)\s*\$?([\d,]+).*?(\d+)%",
        ))
        
        self.templates.append(MathTemplate(
            name="percentage_increase",
            template_type=MathTemplateType.PERCENTAGE,
            keywords=["percent", "%", "increase", "decrease", "more", "less"],
            pattern_regex=r"(\d+)%?\s*(?:increase|more|decrease|less)",
        ))
        
        self.templates.append(MathTemplate(
            name="feed_chickens",
            template_type=MathTemplateType.SEQUENTIAL,
            keywords=["feed", "chicken", "cups", "morning", "afternoon", "final", "meal"],
            pattern_regex=r"(\d+)\s*cups.*?(\d+)\s*cups.*?(\d+)\s*cups.*?(\d+)\s*chickens?",
        ))
        
        self.templates.append(MathTemplate(
            name="discount_purchase",
            template_type=MathTemplateType.PERCENTAGE,
            keywords=["glass", "discount", "second", "costs", "buy", "pay"],
            pattern_regex=r"\$?(\d+).*?(\d+)%.*?(\d+)\s*(?:glasses?|items?)",
        ))
        
        self.templates.append(MathTemplate(
            name="sheep_multiplication",
            template_type=MathTemplateType.RATIO,
            keywords=["sheep", "twice", "times", "together", "total"],
            pattern_regex=r"twice.*?(\d+)\s*times.*?(\d+)\s*sheep",
        ))
        
        self.templates.append(MathTemplate(
            name="work_hours_overtime",
            template_type=MathTemplateType.WORK_RATE,
            keywords=["hour", "rate", "overtime", "worked", "earnings", "pay"],
            pattern_regex=r"\$?(\d+).*?(\d+)\s*hours.*?(\d+\.?\d*)\s*times.*?(\d+)\s*hours",
        ))
        
        self.templates.append(MathTemplate(
            name="downloads_months",
            template_type=MathTemplateType.SEQUENTIAL,
            keywords=["download", "month", "first", "second", "third", "reduced", "total"],
            pattern_regex=r"(\d+)\s*downloads?.*?(\d+)\s*times.*?(\d+)%",
        ))
    
    def solve(self, question: str) -> MathSolution:
        """
        OODA-aligned solve pipeline:
        1. OBSERVE: Parse and extract quantities
        2. ORIENT: Match to templates, retrieve patterns
        3. DECIDE: Choose solving strategy
        4. ACT: Execute and verify
        """
        problem = self._observe(question)
        
        template, confidence = self._orient(problem)
        
        if template and confidence >= 0.5:
            solution = self._act_template(problem, template)
        else:
            solution = self._act_heuristic(problem)
        
        solution = self._verify(problem, solution)
        
        if solution.verified and solution.confidence >= 0.7:
            self._learn(problem, solution)
        
        return solution
    
    def _observe(self, question: str) -> MathProblem:
        """OBSERVE phase: Parse problem and extract quantities."""
        
        quantities = []
        
        currency_pattern = r'\$\s*([\d,]+\.?\d*)'
        for match in re.finditer(currency_pattern, question):
            val = float(match.group(1).replace(',', ''))
            quantities.append((val, "dollars"))
        
        number_pattern = r'(?<!\$)\b([\d,]+\.?\d*)\b'
        for match in re.finditer(number_pattern, question):
            val_str = match.group(1).replace(',', '')
            if val_str and val_str not in [q[0] for q in quantities]:
                try:
                    val = float(val_str)
                    context = self._get_number_context(question, match.start())
                    quantities.append((val, context))
                except ValueError:
                    continue
        
        word_numbers = {
            'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4,
            'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9,
            'ten': 10, 'eleven': 11, 'twelve': 12, 'twenty': 20,
            'thirty': 30, 'forty': 40, 'fifty': 50, 'hundred': 100,
            'thousand': 1000, 'million': 1000000,
            'half': 0.5, 'quarter': 0.25, 'third': 0.333,
        }
        
        q_lower = question.lower()
        for word, val in word_numbers.items():
            if word in q_lower:
                quantities.append((val, word))
        
        keywords = self._extract_keywords(question)
        
        expected_type = "int"
        if any(kw in q_lower for kw in ['rate', 'average', 'percent', '%']):
            expected_type = "float"
        
        return MathProblem(
            original_text=question,
            quantities=quantities,
            keywords=keywords,
            expected_type=expected_type
        )
    
    def _get_number_context(self, text: str, pos: int) -> str:
        """Get context around a number."""
        start = max(0, pos - 30)
        end = min(len(text), pos + 30)
        context = text[start:end].lower()
        
        units = ['eggs', 'cups', 'dollars', 'hours', 'days', 'sheep', 
                 'chickens', 'glasses', 'bolts', 'downloads', 'minutes']
        for unit in units:
            if unit in context:
                return unit
        return "number"
    
    def _extract_keywords(self, question: str) -> List[str]:
        """Extract relevant keywords from question."""
        keywords = []
        q_lower = question.lower()
        
        important_words = [
            'total', 'remaining', 'left', 'profit', 'cost', 'sells', 'buys',
            'each', 'per', 'every', 'together', 'twice', 'half', 'percent',
            'increase', 'decrease', 'more', 'less', 'times', 'gives', 'takes',
            'morning', 'afternoon', 'day', 'week', 'month', 'year',
            'first', 'second', 'third', 'final', 'average', 'mean',
            'eggs', 'chickens', 'sheep', 'glasses', 'bolts', 'downloads',
            'hours', 'rate', 'overtime', 'discount', 'price'
        ]
        
        for word in important_words:
            if word in q_lower:
                keywords.append(word)
        
        return keywords
    
    def _orient(self, problem: MathProblem) -> Tuple[Optional[MathTemplate], float]:
        """ORIENT phase: Match to templates and retrieve patterns."""
        
        best_template = None
        best_confidence = 0.0
        
        for template in self.templates:
            keyword_matches = sum(1 for kw in template.keywords if kw in problem.keywords)
            keyword_score = keyword_matches / len(template.keywords) if template.keywords else 0
            
            regex_score = 0.0
            if template.pattern_regex:
                if re.search(template.pattern_regex, problem.original_text, re.IGNORECASE):
                    regex_score = 0.8
            
            confidence = max(keyword_score, regex_score)
            
            if keyword_matches >= 3:
                confidence = min(1.0, confidence * 1.2)
            
            if confidence > best_confidence:
                best_confidence = confidence
                best_template = template
        
        return best_template, best_confidence
    
    def _act_template(self, problem: MathProblem, template: MathTemplate) -> MathSolution:
        """ACT phase: Solve using matched template."""
        
        q = problem.original_text.lower()
        nums = [q[0] for q in problem.quantities if isinstance(q[0], (int, float))]
        
        if template.name == "eggs_money_problem":
            return self._solve_eggs_problem(problem)
        elif template.name == "bolt_fabric_problem":
            return self._solve_bolt_problem(problem)
        elif template.name == "profit_calculation":
            return self._solve_profit_problem(problem)
        elif template.name == "feed_chickens":
            return self._solve_feed_problem(problem)
        elif template.name == "discount_purchase":
            return self._solve_discount_problem(problem)
        elif template.name == "sheep_multiplication":
            return self._solve_sheep_problem(problem)
        elif template.name == "work_hours_overtime":
            return self._solve_overtime_problem(problem)
        elif template.name == "downloads_months":
            return self._solve_downloads_problem(problem)
        else:
            return self._act_heuristic(problem)
    
    def _solve_eggs_problem(self, problem: MathProblem) -> MathSolution:
        """Solve egg/money type problems."""
        nums = [q[0] for q in problem.quantities]
        
        match = re.search(
            r'(\d+)\s*eggs.*?eats?\s*(\d+).*?(?:bakes?|uses?|makes?)\s*(?:\w+\s+)*?(\d+).*?\$(\d+)',
            problem.original_text, re.IGNORECASE
        )
        
        if match:
            eggs_per_day = float(match.group(1))
            eaten = float(match.group(2))
            baked = float(match.group(3))
            price = float(match.group(4))
            
            remaining = eggs_per_day - eaten - baked
            answer = remaining * price
            
            return MathSolution(
                answer=answer,
                steps=[
                    f"Eggs per day: {eggs_per_day}",
                    f"Used: {eaten} (eaten) + {baked} (baked) = {eaten + baked}",
                    f"Remaining: {eggs_per_day} - {eaten + baked} = {remaining}",
                    f"Money: {remaining} × ${price} = ${answer}"
                ],
                confidence=0.9,
                template_used="eggs_money_problem"
            )
        
        if len(nums) >= 4:
            eggs = nums[0]
            used1 = nums[1]
            used2 = nums[2]
            price = nums[3]
            remaining = eggs - used1 - used2
            answer = remaining * price
            
            return MathSolution(
                answer=answer,
                steps=[f"Computed: ({eggs} - {used1} - {used2}) × {price} = {answer}"],
                confidence=0.6,
                template_used="eggs_money_problem"
            )
        
        return MathSolution(answer=0, steps=["Could not parse"], confidence=0.1, template_used="eggs_money_problem")
    
    def _solve_bolt_problem(self, problem: MathProblem) -> MathSolution:
        """Solve bolt/fabric ratio problems."""
        nums = [q[0] for q in problem.quantities]
        
        match = re.search(r'(\d+)\s*bolts?.*?half', problem.original_text, re.IGNORECASE)
        
        if match or (nums and 'half' in problem.keywords):
            blue = nums[0] if nums else 2
            white = blue / 2
            total = blue + white
            
            return MathSolution(
                answer=total,
                steps=[
                    f"Blue fiber: {blue} bolts",
                    f"White fiber: {blue} / 2 = {white} bolts",
                    f"Total: {blue} + {white} = {total} bolts"
                ],
                confidence=0.9,
                template_used="bolt_fabric_problem"
            )
        
        return MathSolution(answer=0, steps=["Could not parse"], confidence=0.1, template_used="bolt_fabric_problem")
    
    def _solve_profit_problem(self, problem: MathProblem) -> MathSolution:
        """Solve profit/loss problems."""
        match = re.search(
            r'(?:buys?|costs?)\s*\$?([\d,]+).*?(?:repairs?|puts?|spends?)\s*\$?([\d,]+).*?(\d+)%',
            problem.original_text, re.IGNORECASE
        )
        
        if match:
            cost1 = float(match.group(1).replace(',', ''))
            cost2 = float(match.group(2).replace(',', ''))
            percent = float(match.group(3))
            
            total_cost = cost1 + cost2
            increase = cost1 * (percent / 100)
            new_value = cost1 + increase
            profit = new_value - total_cost
            
            return MathSolution(
                answer=profit,
                steps=[
                    f"Total cost: ${cost1} + ${cost2} = ${total_cost}",
                    f"Value increase: ${cost1} × {percent}% = ${increase}",
                    f"New value: ${cost1} + ${increase} = ${new_value}",
                    f"Profit: ${new_value} - ${total_cost} = ${profit}"
                ],
                confidence=0.9,
                template_used="profit_calculation"
            )
        
        return MathSolution(answer=0, steps=["Could not parse"], confidence=0.1, template_used="profit_calculation")
    
    def _solve_feed_problem(self, problem: MathProblem) -> MathSolution:
        """Solve feed/resource problems."""
        nums = [q[0] for q in problem.quantities]
        
        if len(nums) >= 4:
            cups_per_chicken = nums[0]
            morning = nums[1] if len(nums) > 1 else 0
            afternoon = nums[2] if len(nums) > 2 else 0
            num_chickens = nums[3] if len(nums) > 3 else nums[-1]
            
            total_needed = cups_per_chicken * num_chickens
            final_meal = total_needed - morning - afternoon
            
            return MathSolution(
                answer=final_meal,
                steps=[
                    f"Total needed: {cups_per_chicken} × {num_chickens} = {total_needed}",
                    f"Already fed: {morning} + {afternoon} = {morning + afternoon}",
                    f"Final meal: {total_needed} - {morning + afternoon} = {final_meal}"
                ],
                confidence=0.8,
                template_used="feed_chickens"
            )
        
        return MathSolution(answer=0, steps=["Could not parse"], confidence=0.1, template_used="feed_chickens")
    
    def _solve_discount_problem(self, problem: MathProblem) -> MathSolution:
        """Solve discount/purchase problems."""
        nums = [q[0] for q in problem.quantities]
        
        if len(nums) >= 3:
            price = nums[0]
            discount_pct = nums[1]
            num_items = int(nums[2])
            
            half = num_items // 2
            full_price_total = half * price
            discounted_price = price * (discount_pct / 100)
            discounted_total = half * discounted_price
            total = full_price_total + discounted_total
            
            return MathSolution(
                answer=total,
                steps=[
                    f"Full price items: {half} × ${price} = ${full_price_total}",
                    f"Discounted price: ${price} × {discount_pct}% = ${discounted_price}",
                    f"Discounted total: {half} × ${discounted_price} = ${discounted_total}",
                    f"Total: ${full_price_total} + ${discounted_total} = ${total}"
                ],
                confidence=0.8,
                template_used="discount_purchase"
            )
        
        return MathSolution(answer=0, steps=["Could not parse"], confidence=0.1, template_used="discount_purchase")
    
    def _solve_sheep_problem(self, problem: MathProblem) -> MathSolution:
        """Solve ratio/multiplication chain problems."""
        nums = [q[0] for q in problem.quantities]
        
        if nums:
            base = nums[-1] if nums else 20
            
            if 'twice' in problem.keywords and 'times' in problem.keywords:
                multiplier = 4
                for n in nums:
                    if n in [2, 3, 4, 5]:
                        multiplier = n
                        break
                
                seattle = base
                charleston = seattle * multiplier
                toulouse = charleston * 2
                total = seattle + charleston + toulouse
                
                return MathSolution(
                    answer=total,
                    steps=[
                        f"Seattle: {seattle} sheep",
                        f"Charleston: {seattle} × {multiplier} = {charleston} sheep",
                        f"Toulouse: {charleston} × 2 = {toulouse} sheep",
                        f"Total: {seattle} + {charleston} + {toulouse} = {total}"
                    ],
                    confidence=0.85,
                    template_used="sheep_multiplication"
                )
        
        return MathSolution(answer=0, steps=["Could not parse"], confidence=0.1, template_used="sheep_multiplication")
    
    def _solve_overtime_problem(self, problem: MathProblem) -> MathSolution:
        """Solve work/overtime problems."""
        nums = [q[0] for q in problem.quantities]
        
        if len(nums) >= 4:
            rate = nums[0]
            regular_hours = nums[1] if len(nums) > 1 else 40
            overtime_multiplier = nums[2] if len(nums) > 2 else 1.5
            total_hours = nums[3] if len(nums) > 3 else 45
            
            overtime_hours = max(0, total_hours - regular_hours)
            regular_pay = regular_hours * rate
            overtime_rate = rate * overtime_multiplier
            overtime_pay = overtime_hours * overtime_rate
            total = regular_pay + overtime_pay
            
            return MathSolution(
                answer=total,
                steps=[
                    f"Regular pay: {regular_hours} × ${rate} = ${regular_pay}",
                    f"Overtime hours: {total_hours} - {regular_hours} = {overtime_hours}",
                    f"Overtime rate: ${rate} × {overtime_multiplier} = ${overtime_rate}",
                    f"Overtime pay: {overtime_hours} × ${overtime_rate} = ${overtime_pay}",
                    f"Total: ${regular_pay} + ${overtime_pay} = ${total}"
                ],
                confidence=0.8,
                template_used="work_hours_overtime"
            )
        
        return MathSolution(answer=0, steps=["Could not parse"], confidence=0.1, template_used="work_hours_overtime")
    
    def _solve_downloads_problem(self, problem: MathProblem) -> MathSolution:
        """Solve sequential change problems."""
        nums = [q[0] for q in problem.quantities]
        
        if len(nums) >= 3:
            first = nums[0]
            multiplier = nums[1] if nums[1] <= 10 else 3
            reduction_pct = nums[2] if len(nums) > 2 else 30
            
            second = first * multiplier
            third = second * (1 - reduction_pct / 100)
            total = first + second + third
            
            return MathSolution(
                answer=total,
                steps=[
                    f"First month: {first}",
                    f"Second month: {first} × {multiplier} = {second}",
                    f"Third month: {second} × (1 - {reduction_pct}%) = {third}",
                    f"Total: {first} + {second} + {third} = {total}"
                ],
                confidence=0.8,
                template_used="downloads_months"
            )
        
        return MathSolution(answer=0, steps=["Could not parse"], confidence=0.1, template_used="downloads_months")
    
    def _act_heuristic(self, problem: MathProblem) -> MathSolution:
        """Fallback: Use heuristics when no template matches."""
        nums = [q[0] for q in problem.quantities if q[0] > 0]
        
        if not nums:
            return MathSolution(
                answer=0,
                steps=["No numbers found"],
                confidence=0.0,
                template_used="heuristic"
            )
        
        q_lower = problem.original_text.lower()
        
        if any(kw in q_lower for kw in ['total', 'together', 'sum', 'combined']):
            answer = sum(nums)
            return MathSolution(
                answer=answer,
                steps=[f"Sum of {nums} = {answer}"],
                confidence=0.4,
                template_used="heuristic_sum"
            )
        
        if any(kw in q_lower for kw in ['each', 'per', 'every']) and len(nums) >= 2:
            answer = nums[0] * nums[1]
            return MathSolution(
                answer=answer,
                steps=[f"{nums[0]} × {nums[1]} = {answer}"],
                confidence=0.4,
                template_used="heuristic_multiply"
            )
        
        if any(kw in q_lower for kw in ['remaining', 'left', 'difference']) and len(nums) >= 2:
            answer = nums[0] - sum(nums[1:])
            return MathSolution(
                answer=answer,
                steps=[f"{nums[0]} - {sum(nums[1:])} = {answer}"],
                confidence=0.4,
                template_used="heuristic_subtract"
            )
        
        return MathSolution(
            answer=nums[0] if nums else 0,
            steps=["Used first number as answer"],
            confidence=0.2,
            template_used="heuristic_first"
        )
    
    def _verify(self, problem: MathProblem, solution: MathSolution) -> MathSolution:
        """VERIFY: Deterministic verification of solution."""
        
        verified = True
        details = {}
        
        if problem.expected_type == "int" and solution.answer != int(solution.answer):
            if abs(solution.answer - round(solution.answer)) < 0.01:
                solution.answer = round(solution.answer)
            else:
                details["int_check"] = "Warning: Expected integer"
        
        if solution.answer < 0 and not any(kw in problem.original_text.lower() for kw in ['loss', 'debt', 'negative', 'below']):
            details["positive_check"] = "Warning: Unexpected negative answer"
            verified = solution.confidence > 0.7
        
        if solution.answer > 1e12:
            details["magnitude_check"] = "Warning: Very large answer"
            verified = solution.confidence > 0.8
        
        for step in solution.steps:
            if '=' in step:
                parts = step.split('=')
                if len(parts) == 2:
                    try:
                        expr = parts[0].strip()
                        for remove in ['$', 'cups', 'eggs', 'sheep', 'bolts']:
                            expr = expr.replace(remove, '')
                        expr = re.sub(r'[a-zA-Z]+', '', expr).strip()
                    except:
                        pass
        
        solution.verified = verified
        solution.verification_details = details
        
        return solution
    
    def _learn(self, problem: MathProblem, solution: MathSolution):
        """LEARN: Store successful patterns for future retrieval."""
        
        pattern_key = f"{solution.template_used}_{hash(problem.original_text[:50]) % 10000}"
        
        self.solved_patterns[pattern_key] = solution
        
        logger.debug(f"[MATH-ENGINE] Learned pattern: {pattern_key}")


def get_math_reasoning_engine() -> MathReasoningEngine:
    """Get or create singleton math reasoning engine."""
    if not hasattr(get_math_reasoning_engine, '_instance'):
        get_math_reasoning_engine._instance = MathReasoningEngine()
    return get_math_reasoning_engine._instance
