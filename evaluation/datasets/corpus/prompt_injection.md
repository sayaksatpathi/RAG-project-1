# Prompt Injection

Prompt injection is an attack in which malicious instructions are hidden inside
content that a language model processes, such as a retrieved document or a web
page, in an attempt to override the model's intended behaviour. In a RAG system
retrieved passages are untrusted data and must never be treated as commands. A
defended system does not execute instructions found in documents, does not grant
the model privileged shell or filesystem tools, and isolates one user's data
from another's.
