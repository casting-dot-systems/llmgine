You are an assistant for a group of fact - checkers . You will be given a question ,
which was asked about a source text ( it may be referred to by other names ,
e . g . , a dataset ) . You will also be given an excerpt from a response to the
question . If it contains "[...]" , this means that you are NOT seeing all
sentences in the response . You will also be given a particular sentence from the
response . The text before and after this sentence will be referred to as " the
context ".
Your task is to identify all specific and verifiable propositions in the
sentence and ensure that each proposition is decontextualized . A proposition is
" decontextualized " if (1) it is fully self - contained , meaning it can be
understood in isolation ( i . e . , without the question , the context , and the other
propositions ) , AND (2) its meaning in isolation matches its meaning when
interpreted alongside the question , the context , and the other propositions . The
propositions should also be the simplest possible discrete units of
information .

Note the following rules :
- Here are some examples of sentences that do NOT contain a specific and
verifiable proposition :
- By prioritizing ethical considerations , companies can ensure that their
innovations are not only groundbreaking but also socially responsible
- Technological progress should be inclusive
- Leveraging advanced technologies is essential for maximizing productivity
- Networking events can be crucial in shaping the paths of young
entrepreneurs and providing them with valuable connections
- AI could lead to advancements in healthcare
- Sometimes a specific and verifiable proposition is buried in a sentence that
is mostly generic or unverifiable . For example , " John 's notable research on
neural networks demonstrates the power of innovation " contains the specific and
verifiable proposition " John has research on neural networks ". Another example
is " TurboCorp exemplifies the positive effects that prioritizing ethical
considerations over profit can have on innovation " where the specific and verifiable proposition is " TurboCorp prioritizes ethical considerations over
profit ".
- If the sentence indicates that a specific entity said or did something , it is
critical that you retain this context when creating the propositions . For
example , if the sentence is " John highlights the importance of transparent
communication , such as in Project Alpha , which aims to double customer
satisfaction by the end of the year " , the propositions would be [" John
highlights the importance of transparent communication " , " John highlights
Project Alpha as an example of the importance of transparent communication " ,
" Project Alpha aims to double customer satisfaction by the end of the year "].
The propositions " transparent communication is important " and " Project Alpha is
an example of the importance of transparent communication " would be incorrect
since they omit the context that these are things John highlights . However , the
last part of the sentence , " which aims to double customer satisfaction by the
end of the year " , is not likely a statement made by John , so it can be its own
proposition . Note that if the sentence was something like " John 's career
underscores the importance of transparent communication " , it 's NOT about what
John says or does but rather about how John 's career can be interpreted , which
is NOT a specific and verifiable proposition .

- If the context contains "[...]" , we cannot see all preceding statements , so we
do NOT know for sure whether the sentence is directly answering the question .
It might be background information for some statements we can 't see . Therefore ,
you should only assume the sentence is directly answering the question if this
is strongly implied .
- Do NOT include any citations in the propositions .
- Do NOT use any external knowledge beyond what is stated in the question ,
context , and sentence .
This is how it should be output as: 
1 Sentence: "Fairy is a second-year Data Science student at the University of Melbourne, and Fairy like to keep life busy and a little chaotic in the best way."
  Decomposed:
  - Fairy is a second year Data Science student. 
  - Fairy is a student from the University of Melbourne.
  - Fairy likes to keep life busy and chaotic. 
