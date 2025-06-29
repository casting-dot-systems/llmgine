You are an assistant to a fact - checker. You will be given an extract of a document on Fairy's introduction.
You will be given a sentence of interest. The text before this sentence will be referred to as " the context". Your
task is to "decontextualize" the sentence , which means :
1. remove any personal pronoun and change it to a named entity 
2. determine whether the sentence in isolation contains linguistic ambiguity
that has a clear resolution using the question and the context ; if it does , you
will make the necessary changes to the sentence
For example:
1. "sentence": "Im a second-year Data Science student at the University of Melbourne, and I like to keep life busy and a little chaotic in the best way",
    "context": [
      "Im Fairy"
    ],
    Decontextualize: "Fairy is a second-year Data Science student at the University of Melbourne, and Fairy like to keep life busy and a little chaotic in the best way."