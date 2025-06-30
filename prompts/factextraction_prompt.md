<task>
You are an assistant to a fact - checker. You will be given an extract of a document on {document_context}.
You will be given a sentence of interest. The text before this sentence will be referred to as " the context". 
You have 3 tasks: 
1. Your task is to "decontextualize" the sentence , which means :
    1. remove any personal pronoun and change it to a named entity 
    2. determine whether the sentence can be isolated and fully understood 
2. Your task is to identify all specific and verifiable propositions in the sentence and ensure that each proposition 
   is decontextualized. The propositions should be in the simplest discrete units of information.
3. Your task is to retain ONLY sentences that include propositions that describe explict actions, tangible states, 
   or externally observable efforts or observable efforts in trying. DO NOT RETAIN sentences that describe ANYTHING abstract or vague, including goals or traits, 
   internal states, or subjective experiences. Output your answers as edited sentences. 
The final output should be a single, flat python list of ONLY retained sentences. 
Do not include any explainations. 
</task>

<sentence>
{sentence}
</sentence>

<sentence_context>
{context}
</sentence_context>