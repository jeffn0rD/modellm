###############################################################3

## TODO:
X  - need to create a library to facilitate typedb v3 database operations
X    - agents keep messing up syntax with version 2.  the fix is to just create our own api (get it right once)
X    - have to develop a spec for match, insert, delete operations
X  - need a tool that can delete and create a new typedb database.  could possibly be integrated into the above library.  the schema tql file should be seperate, not integrated into the script.
  - need a README.md in project root
  - need to streamlining the prompt pipeline to go from NL informal specification to typedb database
    - prompts are in `prompts` folder.
    - nanocoder integration would be great. possibly a MCP call?
      - create a folder and start nanocoder within that path
      - copy/create the NL application specification file in subfolder `./spec`
      - run first stage of pipeline `prompt_step1_v2.md`.  This would be the MCP call
        - the prompt processed by a (openrouter) call to LLM (model as parameter in MCP call?)
        - yaml file returned by LLM, validated and then needs to go into the `./spec` folder
        - repeated calls for the other steps, json outputs would go to `./spec/json`
        - typedb import with typedb_import.py tool (yaml and json files).  another MCP call?
        - this gets to conceptual model phase.  refinement and implementation are next (see below)
    - an alternative would to use `nanocoder run` from the commandline (or a python CLI) as a batch to process the NL spec and create the typedb database
  - tool/typedb_import.py 
    - needs better looking output, use colors and add switches for verbosity
    - default verbosity should only output errors, and summary of entities and relations created
    - the intent was to have this tool import both json and yaml, a library should be created with logic 
      from this tool and typedb_concepts_import.py
  - next step is to figure out how to integrate the database with LLM agentic reasoning
    - the database now stands as a 'conceptual model' for a software application.  a design to begin fleshing out the architecture and implementation needs to be specified.
    - part of this will be the ability to query the database in a sensical way.  Maybe a list of common queries should be developed, e.g., 'What are the sequence of messages related to action X?'; 'What concepts are affected by a change to text block X in the specification?'; 'What other concepts are needed to implement requirement X?'; etc.
