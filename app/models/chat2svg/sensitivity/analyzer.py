"""
Sensitivity Analysis for Chat2SVG Pipeline Optimization (OR-Tools Version).

This module provides tools for analyzing the sensitivity of different parameters
in the SVG generation pipeline using Google OR-Tools.

Full Analysis Workflow:
1. Initialize analyzer
2. Create optimization model
3. Solve model
4. Run sensitivity analysis
5. Generate recommendations

Example:
>>> analyzer = SensitivityAnalyzer()
>>> model = analyzer.create_optimization_model(requests, resources)
>>> status = model.Solve()
>>> analysis = analyzer.analyze_model(model)
>>> print(analyzer.generate_recommendations(analysis))
"""

import logging
import sys
import time
import numpy as np
from typing import Dict, Any, List, Optional, Tuple, Union
from ortools.linear_solver import pywraplp
from ortools.init import pywrapinit

logger = logging.getLogger(__name__)


class AnalysisError(Exception):
    """Base class for analysis exceptions."""
    pass


class SolverError(AnalysisError):
    """Solver-related errors."""
    pass


class ModelError(AnalysisError):
    """Model construction errors."""
    pass


class AnalysisConfig:
    """Configuration for sensitivity analysis parameters."""
    
    def __init__(self,
                 impact_threshold=0.2,
                 resource_alert_level=0.8,
                 sigmoid_scale=0.1):
        """
        Initialize analysis configuration.
        
        Args:
            impact_threshold: Minimum threshold for considering an impact significant
            resource_alert_level: Threshold for resource constraint alerts
            sigmoid_scale: Scale factor for sigmoid normalization
        """
        self.impact_threshold = impact_threshold
        self.resource_alert_level = resource_alert_level
        self.sigmoid_scale = sigmoid_scale


class SolverContext:
    """Context manager for OR-Tools solver."""
    
    def __init__(self, solver_type='SCIP'):
        """Initialize solver context with specified solver type."""
        self.solver_type = solver_type
        self.solver = None
        
    def __enter__(self):
        """Create and return the solver."""
        try:
            self.solver = pywraplp.Solver.CreateSolver(self.solver_type)
            if not self.solver:
                # Try fallback solver if primary is not available
                self.solver = pywraplp.Solver.CreateSolver('CBC_MIXED_INTEGER_PROGRAMMING')
                if self.solver:
                    logger.warning(f"Primary solver {self.solver_type} not available, using CBC")
                else:
                    raise SolverError("Failed to create solver")
            return self.solver
        except Exception as e:
            raise SolverError(f"Error initializing solver: {e}")
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up solver resources."""
        if self.solver:
            # Nothing explicit to clean here, but we might need to add cleanup
            # operations in the future
            pass


class SensitivityAnalyzer:
    """
    OR-Tools based sensitivity analyzer for Chat2SVG pipeline optimization.
    
    Features:
    - Advanced constraint sensitivity analysis
    - Variable impact quantification
    - Resource bottleneck detection
    - What-if scenario modeling
    """
    
    # Resource requirements per stage - configurable class property
    RESOURCE_SPEC = {
        "template": {"cpu": 0.1, "memory": 0.1, "gpu": 0.0, "vram": 0.1},
        "detail": {"cpu": 0.4, "memory": 0.4, "gpu": 0.8, "vram": 0.7},
        "optimize": {"cpu": 0.3, "memory": 0.2, "gpu": 0.3, "vram": 0.4}
    }
    
    # Minimum impact threshold to avoid false positives
    MIN_IMPACT_THRESHOLD = 1e-5

    def __init__(self, config=None):
        """
        Initialize the OR-Tools based analyzer.
        
        Args:
            config: Optional AnalysisConfig instance
        """
        self.config = config or AnalysisConfig()
        self.stage_impacts = {
            "template": 0.0,
            "detail": 0.0,
            "optimize": 0.0
        }
        self.resource_impacts = {
            "cpu": 0.0,
            "memory": 0.0,
            "gpu": 0.0,
            "vram": 0.0
        }
        self._solver = None
        self._model = None
        
        try:
            pywrapinit.CppBridge.InitLogging("sensitivity_analyzer")
            # Implement solver fallback mechanism
            self._solver = pywraplp.Solver.CreateSolver('SCIP')
            if not self._solver:
                self._solver = pywraplp.Solver.CreateSolver('CBC_MIXED_INTEGER_PROGRAMMING')
                if self._solver:
                    logger.warning("SCIP solver not available, falling back to CBC")
                else:
                    logger.error("Failed to create solver")
            else:
                logger.info("OR-Tools SCIP solver initialized successfully")
        except Exception as e:
            logger.error(f"OR-Tools initialization failed: {e}")
            self._solver = None

    def __del__(self):
        """Clean up resources when the analyzer is deleted."""
        if self._solver:
            # Clear the solver to free up memory
            self._solver.Clear()
            del self._solver

    def analyze_model(self, model: pywraplp.Solver) -> Dict[str, Any]:
        """
        Comprehensive analysis of optimized OR-Tools model.
        
        Args:
            model: Solved OR-Tools model instance
            
        Returns:
            Dict with complete sensitivity analysis results
        """
        start_time = time.monotonic()
        
        if not self._solver:
            return {"error": "Solver not initialized"}
            
        try:
            # Check if the model was solved successfully
            status = model.Solve()
            if status not in [pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE]:
                 raise SolverError(f"Model not solved optimally or feasibly. Status: {status}")

            analysis = {
                "variable_analysis": self._analyze_variables(model),
                "constraint_analysis": self._analyze_constraints(model),
                "stage_impacts": self._calculate_stage_impacts(model),
                "resource_sensitivity": self._calculate_resource_sensitivity(model),
                "stability": self._calculate_solution_stability(model) # Note: Stability calculation is basic
            }
            
            # Record telemetry
            duration = time.monotonic() - start_time
            self._record_telemetry(
                duration=duration,
                num_vars=model.NumVariables(),
                num_constraints=model.NumConstraints()
            )
            
            return analysis
            
        except SolverError as e:
             logger.error(f"Solver error during analysis: {e}")
             return {"error": str(e)}
        except Exception as e:
            logger.error(f"Model analysis failed: {e}", exc_info=True)
            return {"error": str(e)}

    def _record_telemetry(self, duration: float, num_vars: int, num_constraints: int):
        """
        Record telemetry for performance monitoring.
        
        Args:
            duration: Analysis duration in seconds
            num_vars: Number of variables in the model
            num_constraints: Number of constraints in the model
        """
        logger.debug(
            f"Analysis telemetry: duration={duration:.3f}s, vars={num_vars}, constraints={num_constraints}"
        )
        # Here you could add actual metrics collection or monitoring system integration

    def _analyze_variables(self, model: pywraplp.Solver) -> Dict[str, Any]:
        """
        Deep analysis of decision variables, including basis status.
        
        Args:
            model: The solved OR-Tools model
            
        Returns:
            Dict containing variable analysis results
        """
        var_analysis = {}
        
        try:
            for i in range(model.NumVariables()):
                var = model.variable(i)
                var_name = var.name()
                basis_status = var.basis_status() # Get basis status
                
                var_analysis[var_name] = {
                    "value": var.solution_value(),
                    "reduced_cost": var.reduced_cost(),
                    "basis_status": basis_status, # Store basis status
                    "objective_coefficient_range": self._variable_objective_range(var, basis_status, model.Objective().maximization())
                }
                
            return var_analysis
        except AttributeError:
             logger.warning("Basis status not available for this solver. Objective ranges will be approximate.")
             # Fallback if basis_status() is not available
             for i in range(model.NumVariables()):
                 var = model.variable(i)
                 var_name = var.name()
                 var_analysis[var_name] = {
                     "value": var.solution_value(),
                     "reduced_cost": var.reduced_cost(),
                     "basis_status": "UNKNOWN",
                     "objective_coefficient_range": self._variable_objective_range(var, None, model.Objective().maximization())
                 }
             return var_analysis
        except Exception as e:
            logger.error(f"Variable analysis failed: {e}")
            return {"error": str(e)}

    def _variable_objective_range(self, var: pywraplp.Variable, basis_status: Optional[int], is_maximization: bool) -> Tuple[Union[float, str], Union[float, str]]:
        """
        Estimate the allowable range for the variable's objective coefficient
        while maintaining the current basis optimality.

        Note: This provides exact ranges for non-basic variables based on reduced cost.
        Calculating exact ranges for basic variables is complex and often requires
        solver-specific ranging functions not directly exposed here. This method
        returns ('BASIC_VAR_RANGE_NA', 'BASIC_VAR_RANGE_NA') for basic variables.

        Args:
            var: The variable to analyze.
            basis_status: The basis status of the variable (e.g., BASIC, AT_LOWER_BOUND).
                          Can be None if not available.
            is_maximization: True if the objective is maximization, False otherwise.

        Returns:
            Tuple of (allowable_decrease, allowable_increase) for the objective coefficient.
            Values can be float or 'INFINITY'.
        """
        try:
            current_coef = var.objective_coefficient()
            reduced_cost = var.reduced_cost()
            
            # Define constants if basis_status is available
            BASIC = pywraplp.Solver.BasisStatus.BASIC if basis_status is not None else -1
            AT_LOWER_BOUND = pywraplp.Solver.BasisStatus.AT_LOWER_BOUND if basis_status is not None else -1
            AT_UPPER_BOUND = pywraplp.Solver.BasisStatus.AT_UPPER_BOUND if basis_status is not None else -1
            FREE = pywraplp.Solver.BasisStatus.FREE if basis_status is not None else -1
            FIXED_VALUE = pywraplp.Solver.BasisStatus.FIXED_VALUE if basis_status is not None else -1

            allowable_decrease = 0.0
            allowable_increase = 0.0

            if basis_status == BASIC:
                # Exact range calculation for basic variables is complex and
                # typically requires solver-specific ranging functions.
                # We return a placeholder indicating it's not calculated here.
                return ('BASIC_VAR_RANGE_NA', 'BASIC_VAR_RANGE_NA')
            elif basis_status == AT_LOWER_BOUND:
                # Variable is at its lower bound.
                if is_maximization:
                    # Coef can decrease by reduced_cost before var might increase.
                    # Coef can increase indefinitely without changing the basis.
                    allowable_decrease = abs(reduced_cost) if reduced_cost <= 0 else 'INFINITY'
                    allowable_increase = 'INFINITY' if reduced_cost <= 0 else abs(reduced_cost)
                else: # Minimization
                    # Coef can increase by reduced_cost before var might increase.
                    # Coef can decrease indefinitely.
                    allowable_increase = abs(reduced_cost) if reduced_cost >= 0 else 'INFINITY'
                    allowable_decrease = 'INFINITY' if reduced_cost >= 0 else abs(reduced_cost)
            elif basis_status == AT_UPPER_BOUND:
                 # Variable is at its upper bound.
                if is_maximization:
                    # Coef can increase by reduced_cost before var might decrease.
                    # Coef can decrease indefinitely.
                    allowable_increase = abs(reduced_cost) if reduced_cost >= 0 else 'INFINITY'
                    allowable_decrease = 'INFINITY' if reduced_cost >= 0 else abs(reduced_cost)
                else: # Minimization
                    # Coef can decrease by reduced_cost before var might decrease.
                    # Coef can increase indefinitely.
                    allowable_decrease = abs(reduced_cost) if reduced_cost <= 0 else 'INFINITY'
                    allowable_increase = 'INFINITY' if reduced_cost <= 0 else abs(reduced_cost)
            elif basis_status in [FREE, FIXED_VALUE]:
                 # For free or fixed variables, sensitivity is often complex or zero.
                 # Reduced cost should be near zero if optimal.
                 if abs(reduced_cost) < 1e-9:
                     allowable_decrease = 'INFINITY'
                     allowable_increase = 'INFINITY'
                 else:
                     # Non-zero reduced cost might indicate issues or specific model types
                     allowable_decrease = 'CHECK_MODEL'
                     allowable_increase = 'CHECK_MODEL'
            else: # Unknown or unsupported status
                 logger.warning(f"Unknown or unsupported basis status {basis_status} for var {var.name()}. Cannot calculate objective range.")
                 return ('UNKNOWN_STATUS', 'UNKNOWN_STATUS')

            # Return the range relative to the current coefficient
            lower_bound = current_coef - allowable_decrease if isinstance(allowable_decrease, (int, float)) else '-INFINITY'
            upper_bound = current_coef + allowable_increase if isinstance(allowable_increase, (int, float)) else 'INFINITY'

            return (lower_bound, upper_bound)

        except AttributeError:
             # Fallback if basis_status() or other methods are not available
             logger.warning(f"Objective range calculation failed for {var.name()} due to missing solver features. Returning variable bounds instead.")
             lb = var.lb() if var.lb() > -np.inf else 'UNBOUNDED'
             ub = var.ub() if var.ub() < np.inf else 'UNBOUNDED'
             return (f"VAR_BOUND:{lb}", f"VAR_BOUND:{ub}") # Indicate these are var bounds
        except Exception as e:
            logger.warning(f"Objective range calculation failed for {var.name()}: {e}")
            return ('ERROR', 'ERROR')


    def _analyze_constraints(self, model: pywraplp.Solver) -> Dict[str, Any]:
        """
        Detailed constraint sensitivity analysis, including dual values.
        
        Args:
            model: The solved OR-Tools model
            
        Returns:
            Dict containing constraint analysis results
        """
        constraint_analysis = {}
        
        try:
            for i in range(model.NumConstraints()):
                constraint = model.constraint(i)
                constraint_name = constraint.name()
                
                # Calculate slack (handle potential infinity)
                ub = constraint.ub()
                activity = constraint.activity()
                slack = float('inf') if ub == float('inf') else ub - activity

                constraint_analysis[constraint_name] = {
                    "dual_value": constraint.dual_value(),
                    "activity": activity,
                    "bounds": (constraint.lb(), ub),
                    "slack": slack
                    # Note: Calculating RHS range requires more advanced analysis
                }
                
            return constraint_analysis
        except AttributeError:
             logger.warning("Dual values not available for this solver. Constraint analysis will be limited.")
             # Fallback if dual_value() is not available
             for i in range(model.NumConstraints()):
                 constraint = model.constraint(i)
                 constraint_name = constraint.name()
                 ub = constraint.ub()
                 activity = constraint.activity()
                 slack = float('inf') if ub == float('inf') else ub - activity
                 constraint_analysis[constraint_name] = {
                     "dual_value": "N/A",
                     "activity": activity,
                     "bounds": (constraint.lb(), ub),
                     "slack": slack
                 }
             return constraint_analysis
        except Exception as e:
            logger.error(f"Constraint analysis failed: {e}")
            return {"error": str(e)}

    def _calculate_stage_impacts(self, model: pywraplp.Solver) -> Dict[str, float]:
        """
        Quantify stage importance using variable solution values and objective coefficients.
        (Changed from using reduced costs as they reflect sub-optimality, not contribution)

        Args:
            model: The solved OR-Tools model

        Returns:
            Dict mapping stages to their impact scores (normalized contribution to objective)
        """
        stage_impacts = {}
        stage_vars = self._group_variables_by_stage(model)
        total_objective_contribution = 0
        stage_contributions = {stage: 0.0 for stage in stage_vars.keys()}

        try:
            # Calculate total contribution of all relevant variables to the objective
            for stage, var_list in stage_vars.items():
                stage_contribution = sum(
                    var.solution_value() * var.objective_coefficient()
                    for var in var_list
                )
                stage_contributions[stage] = stage_contribution
                total_objective_contribution += stage_contribution

            # Normalize stage contributions
            if total_objective_contribution > self.MIN_IMPACT_THRESHOLD:
                for stage, contribution in stage_contributions.items():
                    normalized_impact = contribution / total_objective_contribution
                    # Apply sigmoid for scaling, but impact is based on relative contribution
                    stage_impacts[stage] = self._sigmoid_normalize(normalized_impact * 10) # Scale before sigmoid
            else:
                 stage_impacts = {stage: 0.0 for stage in stage_vars.keys()}

            # Ensure all expected stages are present, even if impact is zero
            for stage in ["template", "detail", "optimize"]:
                if stage not in stage_impacts:
                    stage_impacts[stage] = 0.0

            return stage_impacts

        except Exception as e:
            logger.error(f"Stage impact calculation failed: {e}")
            return {"template": 0.0, "detail": 0.0, "optimize": 0.0, "error": str(e)}


    def _calculate_resource_sensitivity(self, model: pywraplp.Solver) -> Dict[str, float]:
        """
        Calculate resource constraint sensitivity scores based on dual values.
        
        Args:
            model: The solved OR-Tools model
            
        Returns:
            Dict mapping resources to their sensitivity scores
        """
        resource_sensitivity = {}
        
        try:
            for i in range(model.NumConstraints()):
                constraint = model.constraint(i)
                if "resource_" in constraint.name():
                    resource = constraint.name().split("_")[1]
                    # Sensitivity is directly related to the magnitude of the dual value (shadow price)
                    sensitivity = abs(constraint.dual_value())
                    resource_sensitivity[resource] = self._sigmoid_normalize(sensitivity)
                    
            # Ensure all expected resources are present
            for res in ["cpu", "memory", "gpu", "vram"]:
                 if res not in resource_sensitivity:
                      resource_sensitivity[res] = 0.0 # Assume zero sensitivity if constraint missing/not binding

            return resource_sensitivity
        except AttributeError:
             logger.warning("Dual values not available for this solver. Resource sensitivity cannot be calculated accurately.")
             return {"cpu": 0.0, "memory": 0.0, "gpu": 0.0, "vram": 0.0, "error": "Dual values N/A"}
        except Exception as e:
             logger.error(f"Resource sensitivity calculation failed: {e}")
             return {"cpu": 0.0, "memory": 0.0, "gpu": 0.0, "vram": 0.0, "error": str(e)}


    def _calculate_solution_stability(self, model: pywraplp.Solver) -> Dict[str, Any]:
        """
        Calculate basic solution stability metrics.
        Note: This is a simplified stability assessment. True stability analysis
        often involves perturbation or checking the condition number of the basis matrix.

        Args:
            model: The solved OR-Tools model

        Returns:
            Dict containing basic stability metrics
        """
        stability = {
            "objective_coefficient_ranges": {}, # Renamed for clarity
            "constraint_slack_analysis": {} # Changed from arbitrary tolerance
        }

        # Variable objective coefficient ranges (using the refined method)
        var_analysis = self._analyze_variables(model) # Reuse analysis
        if "error" not in var_analysis:
             for name, data in var_analysis.items():
                  stability["objective_coefficient_ranges"][name] = data.get("objective_coefficient_range", ('N/A', 'N/A'))

        # Constraint slack analysis
        constraint_analysis = self._analyze_constraints(model) # Reuse analysis
        if "error" not in constraint_analysis:
             for name, data in constraint_analysis.items():
                  slack = data.get("slack", 'N/A')
                  bounds = data.get("bounds", (None, None))
                  activity = data.get("activity", None)
                  # Calculate relative slack if possible
                  relative_slack = 'N/A'
                  if isinstance(slack, (int, float)) and slack != float('inf') and bounds[1] is not None and bounds[1] != 0:
                       relative_slack = (slack / abs(bounds[1])) * 100 if abs(bounds[1]) > 1e-9 else 0.0
                  elif isinstance(slack, (int, float)) and slack != float('inf') and activity is not None and activity != 0:
                       # Fallback if UB is inf or 0, use activity as denominator
                       relative_slack = (slack / abs(activity)) * 100 if abs(activity) > 1e-9 else 0.0

                  stability["constraint_slack_analysis"][name] = {
                       "slack": slack,
                       "relative_slack_percent": relative_slack,
                       "is_binding": abs(slack) < 1e-6 if isinstance(slack, (int, float)) else False
                  }

        return stability

    def _group_variables_by_stage(self, model: pywraplp.Solver) -> Dict[str, List]:
        """
        Organize variables by processing stage based on naming convention.
        
        Args:
            model: The OR-Tools model
            
        Returns:
            Dict mapping stages to lists of their variables
        """
        stages = {"template": [], "detail": [], "optimize": []} # Initialize all expected stages
        
        try:
            for i in range(model.NumVariables()):
                var = model.variable(i)
                var_name = var.name()
                # More robust check for stage name within the variable name
                if f'_template' in var_name:
                    stages["template"].append(var)
                elif f'_detail' in var_name:
                    stages["detail"].append(var)
                elif f'_optimize' in var_name:
                    stages["optimize"].append(var)
            return stages
        except Exception as e:
             logger.error(f"Failed to group variables by stage: {e}")
             return stages # Return initialized dict

    def _sigmoid_normalize(self, value: float) -> float:
        """
        Normalize values to [0,1] range using sigmoid function.
        Handles potential overflow for large inputs.
        
        Args:
            value: The value to normalize
            
        Returns:
            Normalized value between 0 and 1
        """
        # Clamp large values to prevent potential overflow in exp
        if value * self.config.sigmoid_scale > 700: # exp(700) is already huge
             return 1.0
        if value * self.config.sigmoid_scale < -700:
             return 0.0
             
        try:
            return 1 / (1 + np.exp(-value * self.config.sigmoid_scale))
        except OverflowError:
             logger.warning(f"Overflow encountered in sigmoid normalization for value {value}. Clamping result.")
             return 1.0 if value > 0 else 0.0


    def create_optimization_model(self, requests, resources) -> pywraplp.Solver:
        """
        Create fresh optimization model for pipeline scheduling.
        
        Args:
            requests: List of PipelineState objects
            resources: Available system resources
            
        Returns:
            Configured OR-Tools model instance
        """
        try:
            with SolverContext('SCIP') as model:
                # Instead of looping for variable creation, use batch creation
                # Unfortunately OR-Tools doesn't have a direct batch creation method like NewBoolVarArray
                # We'll optimize the variable creation as much as possible
                
                x = {}  # Dictionary to store variables
                num_requests = len(requests)
                stages_list = ["template", "detail", "optimize"]

                # Create all variables, grouped by stage for potentially better locality
                for stage in stages_list:
                    for i in range(num_requests):
                        x[(i, stage)] = model.BoolVar(f'x_{i}_{stage}')
                
                # Set optimization objective
                objective = model.Objective()
                # Define stage weights based on perceived value or impact
                STAGE_WEIGHTS = {"template": 0.6, "detail": 0.3, "optimize": 0.1}
                
                # Optimize coefficient setting using LinearExpr
                obj_expr = pywraplp.LinearExpr()
                for i in range(num_requests):
                     priority = getattr(requests[i], 'priority', 0.5) # Get priority or default
                     for stage in stages_list:
                          obj_expr.AddTerm(x[(i, stage)], priority * STAGE_WEIGHTS[stage])

                model.SetObjective(obj_expr)
                objective.SetMaximization()
                
                # Add resource constraints - optimized version
                available_resources = ["cpu", "memory", "gpu", "vram"]
                for res in available_resources:
                    if res in resources: # Only add constraint if resource is tracked
                        # Create expression using LinearExpr for efficiency
                        expr = pywraplp.LinearExpr()
                        for i in range(num_requests):
                            for stage in stages_list:
                                # Check if stage uses this resource and add term
                                stage_req = self.RESOURCE_SPEC.get(stage, {}).get(res, 0)
                                if stage_req > 0:
                                    expr.AddTerm(x[(i, stage)], stage_req)
                                    
                        # Add the constraint only if the expression is not empty
                        if len(expr.GetCoeffs()) > 0:
                             model.Add(expr <= resources[res], f"resource_{res}")
                
                # Add stage dependencies
                for i in range(num_requests):
                    # Detail requires template
                    model.Add(x[(i, "detail")] <= x[(i, "template")], f"dep_t_d_{i}")
                    # Optimize requires detail
                    model.Add(x[(i, "optimize")] <= x[(i, "detail")], f"dep_d_o_{i}")
                
                self._model = model # Store the created model if needed elsewhere
                return model
                
        except SolverError as e:
            logger.error(f"Solver error during model creation: {e}")
            raise e # Re-raise specific error
        except Exception as e:
            logger.error(f"Model creation failed: {e}", exc_info=True)
            raise ModelError(f"Failed to create model: {e}") # Wrap in custom error

    def solve_and_analyze(self, requests, resources) -> Dict[str, Any]:
        """
        Complete solve-and-analyze workflow. Includes model creation, solving,
        solution extraction, and sensitivity analysis.

        Args:
            requests: List of PipelineState objects
            resources: Available system resources

        Returns:
            Dict with solution and analysis results, or an error message.
        """
        try:
            model = self.create_optimization_model(requests, resources)
            # Model creation already raises exceptions, no need to check for None

            status = model.Solve()

            if status == pywraplp.Solver.OPTIMAL:
                solution = self._extract_solution(model, requests)
                analysis = self.analyze_model(model) # Analyze the already solved model
                return {
                    "solution": solution,
                    "analysis": analysis,
                    "status": "OPTIMAL",
                    "objective_value": model.Objective().Value()
                }
            elif status == pywraplp.Solver.FEASIBLE:
                 solution = self._extract_solution(model, requests)
                 analysis = self.analyze_model(model) # Analyze the feasible solution
                 logger.warning("Solver found a feasible but not proven optimal solution.")
                 return {
                     "solution": solution,
                     "analysis": analysis,
                     "status": "FEASIBLE",
                     "objective_value": model.Objective().Value()
                 }
            else:
                # Handle other statuses like INFEASIBLE, UNBOUNDED, ABNORMAL etc.
                status_str = pywraplp.Solver.StatusName(status)
                logger.error(f"Solver failed to find an optimal or feasible solution. Status: {status_str} ({status})")
                return {"error": f"Solver status: {status_str}", "status": status_str}

        except ModelError as e:
            logger.error(f"Model creation error in solve_and_analyze: {e}")
            return {"error": f"Model creation failed: {e}", "status": "MODEL_ERROR"}
        except SolverError as e:
            logger.error(f"Solver setup error in solve_and_analyze: {e}")
            return {"error": f"Solver setup failed: {e}", "status": "SOLVER_SETUP_ERROR"}
        except Exception as e:
            logger.error(f"Unexpected error in solve_and_analyze: {e}", exc_info=True)
            return {"error": f"Unexpected analysis error: {e}", "status": "UNEXPECTED_ERROR"}


    def _extract_solution(self, model: pywraplp.Solver, requests) -> List[Tuple]:
        """
        Extract solution from solved model.
        
        Args:
            model: The solved OR-Tools model
            requests: The original request list
            
        Returns:
            List of (request, stages_to_run) tuples
        """
        solution = []
        num_requests = len(requests)
        stages_list = ["template", "detail", "optimize"]

        try:
            for i in range(num_requests):
                stages_run = []
                for stage in stages_list:
                    var_name = f'x_{i}_{stage}'
                    var = model.LookupVariable(var_name) # Use LookupVariable for safety
                    if var and var.solution_value() > 0.5: # Check if var exists and is active
                        stages_run.append(stage)
                if stages_run: # Only add if at least one stage is run
                    solution.append((requests[i], stages_run))
            return solution
        except Exception as e:
             logger.error(f"Failed to extract solution: {e}", exc_info=True)
             return [] # Return empty list on error


    def what_if_scenario(self, model: pywraplp.Solver,
                        parameter_changes: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform what-if analysis with modified parameters.

        Args:
            model: Original solved model (assumed to be solved optimally/feasibly).
            parameter_changes: Dict specifying changes, e.g.,
                {
                    "variables": [{"name": "var_name", "new_coef": 1.5}],
                    "constraints": [{"name": "constraint_name", "new_ub": 100.0}]
                }

        Returns:
            Dict with scenario analysis results or an error message.
        """
        try:
            # Clone the original model - essential for non-destructive analysis
            scenario_model = self._clone_model(model)
            if not scenario_model:
                raise ModelError("Failed to clone model for what-if analysis.")

            # Apply parameter changes to the CLONED model
            # --- Variable Objective Coefficient Changes ---
            for change in parameter_changes.get("variables", []):
                var_name = change.get("name")
                new_coef = change.get("new_coef")
                if var_name and new_coef is not None:
                    var = scenario_model.LookupVariable(var_name)
                    if var:
                        scenario_model.objective().SetCoefficient(var, new_coef)
                    else:
                        logger.warning(f"What-if: Variable '{var_name}' not found in cloned model.")

            # --- Constraint Bound Changes ---
            for change in parameter_changes.get("constraints", []):
                constraint_name = change.get("name")
                new_lb = change.get("new_lb")
                new_ub = change.get("new_ub")
                if constraint_name and (new_lb is not None or new_ub is not None):
                     # Need to find the constraint - OR-Tools doesn't have LookupConstraint by name easily
                     constraint = None
                     for i in range(scenario_model.NumConstraints()):
                          if scenario_model.constraint(i).name() == constraint_name:
                               constraint = scenario_model.constraint(i)
                               break
                     if constraint:
                          # Use current bounds if new ones aren't specified
                          final_lb = new_lb if new_lb is not None else constraint.lb()
                          final_ub = new_ub if new_ub is not None else constraint.ub()
                          constraint.SetBounds(final_lb, final_ub)
                     else:
                          logger.warning(f"What-if: Constraint '{constraint_name}' not found in cloned model.")

            # Solve the modified scenario model
            status = scenario_model.Solve()

            if status == pywraplp.Solver.OPTIMAL or status == pywraplp.Solver.FEASIBLE:
                # Extract solution and analyze the scenario model
                # Need the original requests list to map back - assuming it's available or passed differently
                # For now, we'll return analysis without mapped solution items
                scenario_analysis = self.analyze_model(scenario_model)

                return {
                    "status": pywraplp.Solver.StatusName(status),
                    "objective_value": scenario_model.Objective().Value(),
                    "objective_change": scenario_model.Objective().Value() - model.Objective().Value(),
                    # "new_solution": self._extract_solution(scenario_model, requests), # Requires requests list
                    "sensitivity_analysis": scenario_analysis
                }
            else:
                status_str = pywraplp.Solver.StatusName(status)
                logger.warning(f"What-if scenario resulted in non-optimal/feasible status: {status_str}")
                return {"error": f"Scenario solver status: {status_str}", "status": status_str}

        except ModelError as e:
             logger.error(f"Model error during what-if scenario: {e}")
             return {"error": str(e), "status": "MODEL_ERROR"}
        except SolverError as e:
             logger.error(f"Solver error during what-if scenario: {e}")
             return {"error": str(e), "status": "SOLVER_ERROR"}
        except Exception as e:
            logger.error(f"Unexpected error in what-if scenario: {e}", exc_info=True)
            return {"error": f"Unexpected what-if error: {e}", "status": "UNEXPECTED_ERROR"}


    def _clone_model(self, original: pywraplp.Solver) -> Optional[pywraplp.Solver]:
        """
        Clone an OR-Tools model for scenario analysis. Creates a new model
        with the same variables, constraints, and objective structure.

        Args:
            original: The OR-Tools model to clone.

        Returns:
            A new OR-Tools model instance, or None if cloning fails.
        """
        try:
            # Create new solver instance of the same type
            solver_type = original.solver_type()
            cloned = pywraplp.Solver.CreateSolver(solver_type)
            
            if not cloned:
                logger.error(f"Failed to create new solver of type {solver_type} for cloning")
                return None
            
            # --- Clone Variables ---
            var_map = {} # Map original var objects to new var objects
            for i in range(original.NumVariables()):
                orig_var = original.variable(i)
                # Create new variable with same bounds, type (implicit via bounds), and name
                new_var = None
                if orig_var.integer():
                     new_var = cloned.IntVar(orig_var.lb(), orig_var.ub(), orig_var.name())
                else:
                     new_var = cloned.NumVar(orig_var.lb(), orig_var.ub(), orig_var.name())
                var_map[orig_var] = new_var # Use original var object as key

            # --- Clone Objective ---
            cloned_objective = cloned.Objective()
            for orig_var, new_var in var_map.items():
                 coef = original.objective().GetCoefficient(orig_var)
                 if coef != 0: # Avoid setting zero coefficients unnecessarily
                      cloned_objective.SetCoefficient(new_var, coef)
            cloned_objective.SetOffset(original.objective().offset()) # Copy offset too
            # Set objective sense (maximization/minimization)
            if original.objective().maximization():
                cloned_objective.SetMaximization()
            else:
                cloned_objective.SetMinimization()
            
            # --- Clone Constraints ---
            for i in range(original.NumConstraints()):
                orig_ct = original.constraint(i)
                # Rebuild constraint expression using the new variables from var_map
                expr = pywraplp.LinearExpr()
                for orig_var, new_var in var_map.items():
                    coef = orig_ct.GetCoefficient(orig_var)
                    if coef != 0:
                        expr.AddTerm(new_var, coef)
                
                # Add constraint with same bounds and name
                lb = orig_ct.lb()
                ub = orig_ct.ub()
                cloned.Add(lb <= expr <= ub, orig_ct.name())
            
            logger.debug(f"Successfully cloned model with {cloned.NumVariables()} vars and {cloned.NumConstraints()} constraints.")
            return cloned
            
        except Exception as e:
            logger.error(f"Model cloning failed: {e}", exc_info=True)
            return None # Return None on any cloning error

    def generate_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """
        Generate optimization recommendations from analysis results.
        Uses configured thresholds for alerts.

        Args:
            analysis: Dict containing analysis results from analyze_model.

        Returns:
            List of recommendation strings.
        """
        recs = []
        if not isinstance(analysis, dict):
             return ["Error: Invalid analysis input."]
        if "error" in analysis:
             return [f"Cannot generate recommendations due to analysis error: {analysis['error']}"]

        try:
            # --- Resource Recommendations ---
            resource_sensitivity = analysis.get("resource_sensitivity", {})
            if isinstance(resource_sensitivity, dict) and "error" not in resource_sensitivity:
                for res, sensitivity in resource_sensitivity.items():
                     if isinstance(sensitivity, (int, float)):
                          if sensitivity > self.config.resource_alert_level:
                               recs.append(f"Resource Bottleneck: Consider increasing {res.upper()} allocation (sensitivity score: {sensitivity:.2f})")
                          elif sensitivity < 0.1: # Low threshold for suggesting reduction
                               recs.append(f"Resource Underutilized: Consider reducing {res.upper()} allocation (sensitivity score: {sensitivity:.2f})")

            # --- Stage Optimization Recommendations ---
            stage_impacts = analysis.get("stage_impacts", {})
            if isinstance(stage_impacts, dict) and "error" not in stage_impacts:
                 # Find stage with highest impact
                 max_impact_stage = max(stage_impacts, key=stage_impacts.get) if stage_impacts else None
                 if max_impact_stage and stage_impacts[max_impact_stage] > self.config.impact_threshold:
                      recs.append(f"High Impact Stage: Prioritize resources for '{max_impact_stage}' stage (impact score: {stage_impacts[max_impact_stage]:.2f})")

                 # Find stage with lowest impact (if significantly low)
                 min_impact_stage = min(stage_impacts, key=stage_impacts.get) if stage_impacts else None
                 if min_impact_stage and stage_impacts[min_impact_stage] < 0.1 and stage_impacts[min_impact_stage] < stage_impacts.get(max_impact_stage, 1.0) / 5:
                      recs.append(f"Low Impact Stage: Consider making '{min_impact_stage}' optional or reducing its resource usage (impact score: {stage_impacts[min_impact_stage]:.2f})")

            # --- Variable Recommendations (Based on Objective Range) ---
            variable_analysis = analysis.get("variable_analysis", {})
            if isinstance(variable_analysis, dict) and "error" not in variable_analysis:
                 sensitive_vars = []
                 for var_name, data in variable_analysis.items():
                      obj_range = data.get("objective_coefficient_range")
                      if isinstance(obj_range, tuple) and len(obj_range) == 2:
                           # Check if range is narrow (e.g., less than 10% of current coef)
                           # This requires knowing the current coef, which isn't stored here yet.
                           # Alternative: Check if range contains 0 for basic vars (if calculated)
                           # Alternative: Check if reduced cost is high for non-basic vars
                           reduced_cost = data.get("reduced_cost", 0)
                           basis_status = data.get("basis_status")
                           if basis_status != pywraplp.Solver.BasisStatus.BASIC and abs(reduced_cost) > 1.0: # Arbitrary threshold for high reduced cost
                                sensitive_vars.append(f"{var_name} (high reduced cost: {reduced_cost:.2f})")

                 if sensitive_vars:
                      recs.append(f"Review Non-Basic Variables: Consider adjusting objective for: {', '.join(sensitive_vars[:3])}{'...' if len(sensitive_vars) > 3 else ''}")

            # --- Constraint Recommendations (Based on Slack) ---
            stability = analysis.get("stability", {})
            constraint_slack = stability.get("constraint_slack_analysis", {})
            if isinstance(constraint_slack, dict):
                 binding_constraints = []
                 for constraint_name, data in constraint_slack.items():
                      if data.get("is_binding"):
                           binding_constraints.append(constraint_name)
                 if binding_constraints:
                      recs.append(f"Binding Constraints: Resources may be limiting. Check constraints: {', '.join(binding_constraints[:3])}{'...' if len(binding_constraints) > 3 else ''}")

            if not recs:
                 recs.append("Analysis complete. No immediate high-priority recommendations found based on current thresholds.")

            return recs

        except Exception as e:
            logger.error(f"Error generating recommendations: {e}", exc_info=True)
            return [f"Error during recommendation generation: {str(e)}"]


def test_basic_analysis():
    """
    Basic test case for the sensitivity analyzer.
    
    This function creates a simple test scenario and verifies that the analyzer
    can successfully create, solve, and analyze an optimization model.
    """
    class PipelineState:
        """Dummy PipelineState for testing."""
        def __init__(self, prompt, priority=0.5):
            self.prompt = prompt
            self.priority = priority
            # Add other attributes if needed by create_optimization_model
            self.id = prompt # Simple ID

    print("--- Running Basic Sensitivity Analyzer Test ---")
    try:
        analyzer = SensitivityAnalyzer()
        # Define simple requests and resources
        requests = [PipelineState("simple prompt 1"), PipelineState("simple prompt 2", priority=0.8)]
        resources = {"cpu": 1.0, "memory": 2.0, "gpu": 1.0, "vram": 1.0} # Add GPU/VRAM

        # Use solve_and_analyze workflow
        result = analyzer.solve_and_analyze(requests, resources)

        print(f"Solver Status: {result.get('status')}")
        print(f"Objective Value: {result.get('objective_value')}")

        assert "error" not in result, f"Test failed with error: {result.get('error')}"
        assert result.get('status') in ["OPTIMAL", "FEASIBLE"], f"Unexpected solver status: {result.get('status')}"
        assert 'solution' in result, "Missing 'solution' key in result"
        assert 'analysis' in result, "Missing 'analysis' key in result"

        analysis = result['analysis']
        assert "error" not in analysis, f"Analysis sub-dict contains an error: {analysis.get('error')}"

        # Check presence of analysis components
        assert 'variable_analysis' in analysis
        assert 'constraint_analysis' in analysis
        assert 'stage_impacts' in analysis
        assert 'resource_sensitivity' in analysis
        assert 'stability' in analysis

        # Check stage impacts (at least one should likely be > 0 in a simple case)
        assert any(v > 0 for v in analysis['stage_impacts'].values() if isinstance(v, (int, float))), "Expected some stage impact > 0"

        # Generate recommendations
        recommendations = analyzer.generate_recommendations(analysis)
        print("Generated Recommendations:")
        for rec in recommendations:
            print(f"- {rec}")
        assert isinstance(recommendations, list), "Recommendations should be a list"

        print("--- Basic test passed! ---")
        return True
    except Exception as e:
        print(f"--- Test failed with exception: {e} ---", file=sys.stderr)
        logger.error("Test execution failed", exc_info=True)
        return False


if __name__ == "__main__":
    # Configure basic logging for testing
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    # Run basic test when module is executed directly
    test_basic_analysis()
