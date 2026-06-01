id: ${agent_id}
name: ${display}
version: 0.1.0
description: ${display} enriches the security casefile section `${section_field}`.
entrypoint: ado_swarm.agents.${agent_id}.main:build_agent
eval_entrypoint: ado_swarm.agents.${agent_id}.eval:run_eval
skills: []
tools:
  allowed:
    - ${tool}
risk_tier: low
