# EcoRetrofit AI - Architecture & Standards

## The Architecture
This project uses a strictly decoupled Service-Oriented Architecture. 
1. `/src/simulation`: ONLY Sinergym, EnergyPlus, and environment wrappers.
2. `/src/training`: ONLY PyTorch, CQL logic, and dataset loaders.
3. `/src/edge`: ONLY ONNX runtime, BACpypes, and Raspberry Pi scripts. STRICTLY NO PyTorch dependencies allowed here.
4. `/src/web`: ONLY FastAPI and React.

## Strict Coding Standards
* Never fucking use any emojis in the code.
* Use strict Python type hinting for all parameters and return types.
* Write highly modular code; separate logic into distinct files rather than massive monolithic scripts.
* When writing Dockerfiles, prioritize minimal image sizes (e.g., using slim or alpine bases where appropriate).