package awcp.governance

# Tell OPA we are using the modern, strict syntax
import rego.v1

# By default, deny everything! (Zero Trust)
default allow := false

# Rule: Allow execution ONLY IF these conditions are met:
allow if {
    # 1. The agent must provide an ID
    input.agent_id != ""
    
    # 2. The code cannot contain our known crash trigger
    not contains(input.code_to_run, "1/0")
    
    # 3. The code cannot try to access the underlying operating system
    not contains(input.code_to_run, "os.system")
}

