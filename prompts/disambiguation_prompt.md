You are an assistant to a fact - checker . You will be given a question , which was
asked about a source text ( it may be referred to by other names , e . g . , a
dataset ) . You will also be given an excerpt from a response to the question . If
it contains "[...]" , this means that you are NOT seeing all sentences in the
response . You will also be given a particular sentence from the response . The
text before and after this sentence will be referred to as " the context ". Your
task is to " decontextualize " the sentence , which means :
1. determine whether it 's possible to resolve partial names and undefined
acronyms / abbreviations in the sentence using the question and the context ; if it
is possible , you will make the necessary changes to the sentence
2. determine whether the sentence in isolation contains linguistic ambiguity
that has a clear resolution using the question and the context ; if it does , you
will make the necessary changes to the sentence
Note the following rules :
- " Linguistic ambiguity " refers to the presence of multiple possible meanings in
a sentence . Vagueness and generality are NOT linguistic ambiguity . Linguistic
ambiguity includes referential and structural ambiguity . Temporal ambiguity is a
type of referential ambiguity .
- If it is unclear whether the sentence is directly answering the question , you
should NOT count this as linguistic ambiguity . You should NOT add any
information to the sentence that assumes a connection to the question .
- If a name is only partially given in the sentence , but the full name is
provided in the question or the context , the DecontextualizedSentence must
always use the full name . The same rule applies to definitions for acronyms and
abbreviations . However , the lack of a full name or a definition for an acronym /
abbreviation in the question and the context does NOT count as linguistic
ambiguity ; in this case , you will just leave the name , acronym , or abbreviation
as is .
- Do NOT include any citations in the DecontextualizedSentence .
- Do NOT use any external knowledge beyond what is stated in the question ,
context , and sentence .
Here are some correct examples that you should pay attention to :
1. Question = " Describe the history of TurboCorp " , Context = " John Smith was an
early employee who transitioned to management in 2010" , Sentence = " At the time ,
he led the company 's operations and finance teams ."
- For referential ambiguity , " At the time " , " he " , and " the company 's " are
unclear . A group of readers shown the question and the context would likely
reach consensus about the correct interpretation : " At the time " corresponds
to 2010 , " he " refers to John Smith , and " the company 's " refers to TurboCorp .
- DecontextualizedSentence : In 2010 , John Smith led TurboCorp 's operations
and finance teams .
2. Question = " Who are notable executive figures ?" , Context = "[...]** Jane Doe
**" , Sentence = " These notes indicate that her leadership at TurboCorp and
MiniMax is accelerating progress in renewable energy and sustainable
agriculture ."
    - For referential ambiguity , " these notes " and " her " are unclear . A group of readers shown the question and the context would likely fail to reach consensus about the correct interpretation of " these notes " , since there is no indication in the question or context . However , they would likely reach consensus about the correct interpretation of " her ": Jane Doe .
    - For structural ambiguity , the sentence could be interpreted as : (1) Jane 's leadership is accelerating progress in renewable energy and sustainable agriculture at both TurboCorp and MiniMax , (2) Jane 's leadership is
    accelerating progress in renewable energy at TurboCorp and in sustainable agriculture at MiniMax . A group of readers shown the question and the context would likely fail to reach consensus about the correct interpretation of this ambiguity .
    - DecontextualizedSentence : Cannot be decontextualized
3. Question = " Who founded MiniMax ?" , Context = " None " , Sentence = " Executives like John Smith were involved in the early days of MiniMax ."
    - For referential ambiguity , " like John Smith " is unclear . A group of readers shown the question and the context would likely reach consensus about the correct interpretation : John Smith is an example of an executive who was involved in the early days of MiniMax .
- Note that " Involved in " and " the early days " are vague , but they are NOT
linguistic ambiguity .
- DecontextualizedSentence : John Smith is an example of an executive who was
involved in the early days of MiniMax .
4. Question = " What advice is given to young entrepreneurs ?" , Context =
"# Ethical Considerations " , Sentence = " Sustainable manufacturing , as emphasized
by John Smith and Jane Doe , is critical for customer buy - in and long - term
success ."
- For structural ambiguity , the sentence could be interpreted as : (1) John
Smith and Jane Doe emphasized that sustainable manufacturing is critical for
customer buy - in and long - term success , (2) John Smith and Jane Doe
emphasized sustainable manufacturing while the claim that sustainable
manufacturing is critical for customer buy - in and long - term success is
attributable to the writer , not to John Smith and Jane Doe . A group of
readers shown the question and the context would likely fail to reach
consensus about the correct interpretation of this ambiguity .
- DecontextualizedSentence : Cannot be decontextualized
5. Question = " What are common strategies for building successful teams ?" ,
Context = " One of the most common strategies is creating a diverse team ." ,
Sentence = " Last winter , John Smith highlighted the importance of
interdisciplinary discussions and collaborations , which can drive advancements
by integrating diverse perspectives from fields such as artificial intelligence ,
genetic engineering , and statistical machine learning ."
- For referential ambiguity , " Last winter " is unclear . A group of readers
shown the question and the context would likely fail to reach consensus
about the correct interpretation of this ambiguity , since there is no
indication of the time period in the question or context .
- For structural ambiguity , the sentence could be interpreted as : (1) John
Smith highlighted the importance of interdisciplinary discussions and
collaborations and that they can drive advancements by integrating diverse
perspectives from some example fields , (2) John Smith only highlighted the
importance of interdisciplinary discussions and collaborations while the
claim that they can drive advancements by integrating diverse perspectives
from some example fields is attributable to the writer , not to John Smith . A
group of readers shown the question and the context would likely fail to
reach consensus about the correct interpretation of this ambiguity .
- DecontextualizedSentence : Cannot be decontextualized
6. Question = " What opinions are provided on disruptive technologies ?" , Context
= "[...] However , there is a divergence in how to weigh short - term benefits
against long - term risks ." , Sentence = " These differences are illustrated by the
discussion on healthcare : some stress AI 's benefits , while others highlight its
risks , such as privacy and data security ."
- For referential ambiguity , " These differences " is unclear . A group of
readers shown the question and the context would likely reach consensus
about the correct interpretation : the differences are with respect to how to
weigh short - term benefits against long - term risks .
- For structural ambiguity , the sentence could be interpreted as : (1)
privacy and data security are examples of risks , (2) privacy and data
security are examples of both benefits and risks . A group of readers shown
the question and the context would likely reach consensus about the correct
interpretation : privacy and data security are examples of risks .
- Note that " Some " and " others " are vague , but they are not linguistic
ambiguity .
- DecontextualizedSentence : The differences in how to weigh short - term
benefits against long - term risks are illustrated by the discussion on
healthcare . Some experts stress AI 's benefits with respect to healthcare .
Other experts highlight AI 's risks with respect to healthcare , such as
privacy and data security .
First , print " Incomplete Names , Acronyms , Abbreviations :" followed by your step -
by - step reasoning for determining whether the Sentence contains any partial
names and undefined acronyms / abbreviations . If the full names and definitions
are provided in the question or context , the Sentence will be updated
accordingly ; otherwise , they will be left as is and they will NOT count as
linguistic ambiguity . Next , print " Linguistic Ambiguity in '< insert the sentence > ':" followed by your step - by - step reasoning for checking (1)
referential and (2) structural ambiguity ( and note that 1. referential ambiguity
is NOT equivalent to vague or general language and it includes temporal
ambiguity , and 2. structural reasoning must follow " The sentence could be
interpreted as : < insert one or multiple interpretations >") , then considering
whether a group of readers shown the question and the context would likely reach
consensus or fail to reach consensus about the correct interpretation of the
linguistic ambiguity . If they would likely fail to reach consensus , print
" DecontextualizedSentence : Cannot be decontextualized "; otherwise , first print
" Changes Needed to Decontextualize the Sentence :" followed by a list of all
changes needed to ensure the Sentence is fully decontextualized ( e . g . , replace
" executives like John Smith " with " John Smith is an example of an executive who
") and includes all full names and definitions for acronyms / abbreviations ( only
if they were provided in the question and the context ) , then print
" DecontextualizedSentence :" followed by the final sentence ( or collection of
sentences ) that implements all changes .


