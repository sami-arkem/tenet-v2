# FINETUNE PLAN

## phase
- 0.5

## objective
- run first real LoRA fine-tune
- evaluate on gold tests
- track weak cases

## base model
- mistral-7b-instruct

## method
- lora

## training inputs
- data/raw/kyc_cases.jsonl
- data/raw/kyb_cases.jsonl
- data/raw/risk_cases.jsonl
- data/raw/gap_cases.jsonl
- data/raw/document_cases.jsonl
