###############################################################3

## TODO:
  ## NEXT TASKS
  - need to streamlining the prompt pipeline to go from NL informal specification to typedb database
    - prompts are in `prompts` folder.
    - review the prompts
      - prompt_step1_v2.md is designed to generate YAML from NL specification
      - prompt_step2_v2.md will convert the YAML into a more formalized specification .md
      - prompt_step3_v2.md is designed for handling revisions to the formal spec
      - steps 2 and 3 above are only used when a revise/refine cycle is being used to get to an approved specification draft 0.1
      - prompt_step_[C3, C4, C5, D1] are steps that generated json files describing typedb entities
      - the already created tools/typedb_import.py script intakes the yaml and json files generated and creates requisite database entities and relations 
    - a new library needs to be created to handle the generation pipeline
      - it will use openrouter api to execute the prompts and save the outputs
      - different models can be used for different steps
      - the prompts will need the necessary data substituted/appended in from previous steps
        - later revision of the library will utilize some form of compression to keep context minimal and concise
    - a CLI tool needs to be created that will use the library.  switches for model and step and file/folder locations will need to be supplied
      - switches also configurable so entire pipeline can be run (this would exclude the step 2/3 revision cycle) or individual steps.  For simplicity only one switch for model, so if entire pipeline is run it will use the same model
      - a later revision should have a configuration file (yaml) that would allow specification of prefered models for steps
      - some form of validation needs to be done on the outputs (yaml and json).  
      

  ** DO NOT PLAN OR CREATE TASKS FOR ANYTHING AFTER THIS POINT **    
  ## TASKS THAT NEED DETAILED PLANNING AND SPECIFICATION (FUTURE)
  - need to streamlining the prompt pipeline to go from NL informal specification to typedb database
    - prompts are in `prompts` folder.
    - nanocoder integration would be great. possibly a MCP call?
      - nanocoder github project: https://github.com/Nano-Collective/nanocoder
      - create a folder and start nanocoder within that path
      - copy/create the NL application specification file in subfolder `./spec`
      - run first stage of pipeline `prompt_step1_v2.md`.  This would be the MCP call
        - the prompt processed by a (openrouter) call to LLM (model as parameter in MCP call?)
        - yaml file returned by LLM, validated and then needs to go into the `./spec` folder
        - repeated calls for the other steps, json outputs would go to `./spec/json`
        - typedb import with typedb_import.py tool (yaml and json files).  another MCP call?
        - this gets to conceptual model phase.  refinement and implementation are next (see below)
    - an alternative would to use `nanocoder run` from the commandline (or a python CLI) as a batch to process the NL spec and create the typedb database
  - next step is to figure out how to integrate the database with LLM agentic reasoning
    - the database now stands as a 'conceptual model' for a software application.  a design to begin fleshing out the architecture and implementation needs to be specified.
    - part of this will be the ability to query the database in a sensical way.  Maybe a list of common queries should be developed, e.g., 'What are the sequence of messages related to action X?'; 'What concepts are affected by a change to text block X in the specification?'; 'What other concepts are needed to implement requirement X?'; etc.
    - information on LLM interaction with typeDB here: doc\typedb_llm_reasoning.md

## DONE
X  - need to create a library to facilitate typedb v3 database operations
X    - agents keep messing up syntax with version 2.  the fix is to just create our own api (get it right once)
X    - have to develop a spec for match, insert, delete operations
X  - need a tool that can delete and create a new typedb database.  could possibly be integrated into the above library.  the schema tql file should be seperate, not integrated into the script.
X  - need a README.md in project root

X  - tool/typedb_import.py 
X    - needs better looking output, use colors and add switches for verbosity
X    - default verbosity should only output errors, and summary of entities and relations created
X    - the intent was to have this tool import both json and yaml, a library should be created with logic 
X      from this tool and typedb_concepts_import.py
X    - directory re-structuring
X      - /tool and /tools is redundant.  there should be one directory.  lets call it ./tools; thats where the import CLI tool goes
X      - is tools/typedb_concepts_import.py needed anymore? typedb_import.py covers all scenarios (yaml and json)?
X      - the typedb_c3_client library should live in a directory off of root not named tools.  something more python canonical?  module?  lib?
X        - will have to make sure import paths work and pip install
X      - why are there 2 test directories? (tools/tests and ./tests)
X    - typedb_v3_client isn't a great name for a library; lets change to TypeDBClient3  
X    - make sure all test and development temp files are cleaned up -- or moved to agents directory
X    - the README and doc/API.md files do not cover the entire library (Query Nuilder, etc).  Make sure all classes are covered with examples.
X    - TypeDBClient3: need to implement database wipe using schema parsing to determine what entities and relations need to be deleted
