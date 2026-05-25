# RAG System Notes

## Introduction

Retrieval-Augmented Generation, or RAG, is a technique where a language model answers questions using external documents instead of relying only on its internal knowledge.

## Hybrid Retrieval

Hybrid retrieval combines semantic vector search with keyword-based BM25 search. Vector search helps with meaning, while BM25 helps with exact terms and acronyms.

## Evaluation

A production RAG system should be evaluated using retrieval recall, faithfulness, citation coverage, and answer relevance. Evaluation helps detect quality regressions.