import datetime as dt


class MockAdapter:
    def __init__(self):
        self.audit_log = []

    def reset_environment(self):
        self.audit_log = []

    def submit_transaction(self, test_input, primitive="DAE"):
        primitive = (primitive or "DAE").upper()
        if primitive == "DAE":
            return self._evaluate_dae(test_input)
        if primitive == "DBA":
            return self._evaluate_dba(test_input)
        if primitive == "TCR":
            return self._evaluate_tcr(test_input)
        if primitive == "COMBINED":
            return self._evaluate_combined(test_input)
        raise ValueError(f"Unsupported primitive: {primitive}")

    def collect_evidence(self, transaction_id):
        return [e for e in self.audit_log if e.get("transaction_id") == transaction_id]

    def shutdown(self):
        self.audit_log = []
        return {"shutdown": True, "adapter": "mock"}

    def _evaluate_dae(self, test_input, emit_evidence=True):
        delegation = test_input.get("delegation")
        tx = test_input.get("transaction", {})
        tx_id = tx.get("transaction_id", "tx-unknown")
        action = tx.get("action")
        amount = tx.get("amount", 0)

        if delegation is None:
            return self._decision(
                tx_id,
                "deny",
                "ERR_DAE_MISSING",
                None,
                "delegation_id",
                emit_evidence=emit_evidence,
            )

        if delegation.get("revoked", False):
            return self._decision(
                tx_id,
                "deny",
                "ERR_DAE_REVOKED",
                delegation,
                "delegation_id",
                emit_evidence=emit_evidence,
            )

        now = self._now()
        expiry = self._parse_time(delegation["expiry"])
        if now > expiry:
            return self._decision(
                tx_id,
                "deny",
                "ERR_DAE_EXPIRED",
                delegation,
                "delegation_id",
                emit_evidence=emit_evidence,
            )

        if action not in delegation.get("allowed_actions", []):
            return self._decision(
                tx_id,
                "deny",
                "ERR_DAE_ACTION_NOT_ALLOWED",
                delegation,
                "delegation_id",
                emit_evidence=emit_evidence,
            )

        max_value = delegation.get("constraints", {}).get("max_value")
        if max_value is not None and amount > max_value:
            return self._decision(
                tx_id,
                "deny",
                "ERR_DAE_MAX_VALUE_EXCEEDED",
                delegation,
                "delegation_id",
                emit_evidence=emit_evidence,
            )

        return self._decision(
            tx_id,
            "allow",
            "OK_DAE_ALLOWED",
            delegation,
            "delegation_id",
            emit_evidence=emit_evidence,
        )

    def _evaluate_dba(self, test_input, emit_evidence=True):
        assertion = test_input.get("boundary_assertion")
        tx = test_input.get("transaction", {})
        tx_id = tx.get("transaction_id", "tx-unknown")
        operation = tx.get("operation")
        region = tx.get("region")
        requested_retention = tx.get("requested_retention_hours", 0)
        cross_org_transfer = tx.get("cross_org_transfer", False)
        visible_fields = set(tx.get("visible_fields", []))

        if assertion is None:
            return self._decision(
                tx_id,
                "deny",
                "ERR_DBA_MISSING",
                None,
                "assertion_id",
                emit_evidence=emit_evidence,
            )

        constraints = assertion.get("boundary_constraints", {})
        extra = {
            "evaluated_operation": operation,
            "evaluated_region": region,
        }

        if not constraints.get("egress_allowed", True) and cross_org_transfer:
            return self._decision(
                tx_id,
                "deny",
                "ERR_DBA_EGRESS_BLOCKED",
                assertion,
                "assertion_id",
                extra_result=extra,
                emit_evidence=emit_evidence,
            )

        allowed_regions = constraints.get("allowed_regions")
        if allowed_regions and region not in allowed_regions:
            return self._decision(
                tx_id,
                "deny",
                "ERR_DBA_REGION_NOT_ALLOWED",
                assertion,
                "assertion_id",
                extra_result=extra,
                emit_evidence=emit_evidence,
            )

        required_redactions = set(constraints.get("redaction_required", []))
        if required_redactions.intersection(visible_fields):
            return self._decision(
                tx_id,
                "deny",
                "ERR_DBA_REDACTION_REQUIRED",
                assertion,
                "assertion_id",
                extra_result=extra,
                emit_evidence=emit_evidence,
            )

        max_retention = constraints.get("max_retention_hours")
        if max_retention is not None and requested_retention > max_retention:
            return self._decision(
                tx_id,
                "deny",
                "ERR_DBA_RETENTION_EXCEEDED",
                assertion,
                "assertion_id",
                extra_result=extra,
                emit_evidence=emit_evidence,
            )

        if operation not in assertion.get("permitted_operations", []):
            return self._decision(
                tx_id,
                "deny",
                "ERR_DBA_OPERATION_NOT_ALLOWED",
                assertion,
                "assertion_id",
                extra_result=extra,
                emit_evidence=emit_evidence,
            )

        return self._decision(
            tx_id,
            "allow",
            "OK_DBA_ALLOWED",
            assertion,
            "assertion_id",
            extra_result=extra,
            emit_evidence=emit_evidence,
        )

    def _evaluate_tcr(self, test_input, emit_evidence=True):
        record = test_input.get("commitment_record")
        tx = test_input.get("transaction", {})
        tx_id = tx.get("transaction_id")
        if not tx_id and record is not None:
            tx_id = record.get("transaction_id")
        tx_id = tx_id or "tx-unknown"

        if record is None:
            return self._decision(
                tx_id,
                "deny",
                "ERR_TCR_MISSING",
                None,
                "commitment_id",
                emit_evidence=emit_evidence,
            )

        status = record.get("status")
        commitments = record.get("commitments", [])
        extra = {
            "status": status,
            "evidence_ref_count": len(record.get("evidence_refs", [])),
        }

        if status == "revoked":
            return self._decision(
                tx_id,
                "deny",
                "ERR_TCR_REVOKED",
                record,
                "commitment_id",
                extra_result=extra,
                emit_evidence=emit_evidence,
            )

        if status == "breached":
            return self._decision(
                tx_id,
                "deny",
                "ERR_TCR_BREACH_RECORDED",
                record,
                "commitment_id",
                extra_result=extra,
                emit_evidence=emit_evidence,
            )

        now = self._now()
        for commitment in commitments:
            if not commitment.get("required", False) or commitment.get("fulfilled", False):
                continue
            due_by = commitment.get("due_by")
            if due_by and now > self._parse_time(due_by):
                extra["status"] = "breached"
                return self._decision(
                    tx_id,
                    "deny",
                    "ERR_TCR_REQUIRED_COMMITMENT_UNFULFILLED",
                    record,
                    "commitment_id",
                    extra_result=extra,
                    emit_evidence=emit_evidence,
                )

        required_commitments = [c for c in commitments if c.get("required", False)]
        if all(c.get("fulfilled", False) for c in required_commitments):
            extra["status"] = "fulfilled"
            return self._decision(
                tx_id,
                "allow",
                "OK_TCR_FULFILLED",
                record,
                "commitment_id",
                extra_result=extra,
                emit_evidence=emit_evidence,
            )

        extra["status"] = "pending"
        return self._decision(
            tx_id,
            "allow",
            "OK_TCR_PENDING",
            record,
            "commitment_id",
            extra_result=extra,
            emit_evidence=emit_evidence,
        )

    def _evaluate_combined(self, test_input):
        tx = test_input.get("transaction", {})
        tx_id = tx.get("transaction_id", "tx-unknown")
        options = test_input.get("combined_options", {})
        mode = options.get("mode", "first_failure")
        order = self._normalize_precedence(options.get("precedence"))

        phase_data = {
            "evaluation_mode": mode,
            "evaluation_order": order,
            "dae_decision": "not_run",
            "dae_reason_code": "NOT_RUN",
            "dba_decision": "not_run",
            "dba_reason_code": "NOT_RUN",
            "tcr_decision": "not_run",
            "tcr_reason_code": "NOT_RUN",
            "failed_phases": [],
            "failure_reason_codes": [],
        }

        delegation = test_input.get("delegation")
        assertion = test_input.get("boundary_assertion")
        record = test_input.get("commitment_record")
        if delegation and delegation.get("delegation_id"):
            phase_data["delegation_id"] = delegation["delegation_id"]
        if assertion and assertion.get("assertion_id"):
            phase_data["assertion_id"] = assertion["assertion_id"]
        if record and record.get("commitment_id"):
            phase_data["commitment_id"] = record["commitment_id"]

        evaluators = {
            "DAE": lambda: self._evaluate_dae(test_input, emit_evidence=False),
            "DBA": lambda: self._evaluate_dba(test_input, emit_evidence=False),
            "TCR": lambda: self._evaluate_tcr(test_input, emit_evidence=False),
        }

        phase_results = {}
        denied = []
        for phase in order:
            result = evaluators[phase]()
            phase_results[phase] = result
            self._record_phase_result(phase_data, phase, result)
            if result["decision"] == "deny":
                denied.append((phase, result))
                if mode == "first_failure":
                    break

        audit_envelope = {"audit_required": self._combined_audit_required(test_input)}

        if mode == "aggregate":
            if not denied:
                phase_data["final_phase"] = "COMBINED"
                return self._decision(
                    tx_id,
                    "allow",
                    "OK_COMBINED_ALLOWED",
                    audit_envelope,
                    None,
                    extra_result=phase_data,
                )

            if len(denied) == 1:
                failed_phase, failed_result = denied[0]
                phase_data["failed_phase"] = failed_phase
                phase_data["final_phase"] = failed_phase
                return self._decision(
                    tx_id,
                    "deny",
                    failed_result["reason_code"],
                    audit_envelope,
                    None,
                    extra_result=phase_data,
                )

            phase_data["failed_phase"] = "MULTI"
            phase_data["final_phase"] = "MULTI"
            return self._decision(
                tx_id,
                "deny",
                "ERR_COMBINED_MULTI_FAILURE",
                audit_envelope,
                None,
                extra_result=phase_data,
            )

        if denied:
            failed_phase, failed_result = denied[0]
            phase_data["failed_phase"] = failed_phase
            phase_data["final_phase"] = failed_phase
            return self._decision(
                tx_id,
                "deny",
                failed_result["reason_code"],
                audit_envelope,
                None,
                extra_result=phase_data,
            )

        final_phase = order[-1]
        phase_data["final_phase"] = final_phase
        return self._decision(
            tx_id,
            "allow",
            phase_results[final_phase]["reason_code"],
            audit_envelope,
            None,
            extra_result=phase_data,
        )

    def _decision(
        self,
        tx_id,
        decision,
        reason_code,
        artifact,
        artifact_id_key,
        extra_result=None,
        extra_evidence=None,
        emit_evidence=True,
    ):
        result = {
            "transaction_id": tx_id,
            "decision": decision,
            "reason_code": reason_code,
        }
        if artifact and artifact_id_key and artifact.get(artifact_id_key):
            result[artifact_id_key] = artifact.get(artifact_id_key)
        if extra_result:
            result.update(extra_result)

        if emit_evidence and artifact and artifact.get("audit_required", False):
            event = {
                "type": "audit_log",
                "transaction_id": tx_id,
                "decision": decision,
                "reason_code": reason_code,
                "timestamp": self._now().isoformat(),
            }
            if artifact_id_key and artifact.get(artifact_id_key):
                event[artifact_id_key] = artifact.get(artifact_id_key)
            if extra_result:
                event.update(extra_result)
            if extra_evidence:
                event.update(extra_evidence)
            self.audit_log.append(event)
        return result

    def _now(self):
        return dt.datetime.now(dt.timezone.utc)

    def _parse_time(self, value):
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))

    def _combined_audit_required(self, test_input):
        for key in ("delegation", "boundary_assertion", "commitment_record"):
            artifact = test_input.get(key)
            if artifact and artifact.get("audit_required", False):
                return True
        return False

    def _normalize_precedence(self, configured_order):
        default = ["DAE", "DBA", "TCR"]
        if not configured_order:
            return default

        normalized = []
        for phase in configured_order:
            phase_name = str(phase).upper()
            if phase_name in default and phase_name not in normalized:
                normalized.append(phase_name)

        for phase in default:
            if phase not in normalized:
                normalized.append(phase)
        return normalized

    def _record_phase_result(self, phase_data, phase, result):
        lowered = phase.lower()
        phase_data[f"{lowered}_decision"] = result["decision"]
        phase_data[f"{lowered}_reason_code"] = result["reason_code"]
        if result["decision"] == "deny":
            phase_data["failed_phases"].append(phase)
            phase_data["failure_reason_codes"].append(result["reason_code"])
