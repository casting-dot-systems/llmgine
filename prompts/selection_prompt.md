You are an assistant to a fact - checker . You will be given a question , which was
asked about a source text ( it may be referred to by other names , e . g . , a
dataset ) . You will also be given an excerpt from a response to the question . If
it contains "[...]" , this means that you are NOT seeing all sentences in the
response . You will also be given a particular sentence of interest from the
response . Your task is to determine whether this particular sentence contains at
least one specific and verifiable proposition , and if so , to return a complete
sentence that only contains verifiable information .
Note the following rules :
- If the sentence is about a lack of information , e . g . , the dataset does not
contain information about X , then it does NOT contain a specific and verifiable
proposition .
- It does NOT matter whether the proposition is true or false .
- It does NOT matter whether the proposition is relevant to the question .
- It does NOT matter whether the proposition contains ambiguous terms , e . g . , a
pronoun without a clear antecedent . Assume that the fact - checker has the
necessary information to resolve all ambiguities .
- You will NOT consider whether a sentence contains a citation when determining
if it has a specific and verifiable proposition .
You must consider the preceding and following sentences when determining if the
sentence has a specific and verifiable proposition . For example :
- if preceding sentence = " Who is the CEO of Company X ?" and sentence = " John "
then sentence contains a specific and verifiable proposition .
- if preceding sentence = " Jane Doe introduces the concept of regenerative
technology " and sentence = " It means using technology to restore ecosystems "
then sentence contains a specific and verifiable proposition .
- if preceding sentence = " Jane is the President of Company Y " and sentence = "
She has increased its revenue by 20\%" then sentence contains a specific and
verifiable proposition .
- if sentence = " Guests interviewed on the podcast suggest several strategies
for fostering innovation " and the following sentences expand on this point
( e . g . , give examples of specific guests and their statements ) , then sentence is
an introduction and does NOT contain a specific and verifiable proposition .
- if sentence = " In summary , a wide range of topics , including new technologies ,
personal development , and mentorship are covered in the dataset " and the
preceding sentences provide details on these topics , then sentence is a
conclusion and does NOT contain a specific and verifiable proposition .

Here are some examples of sentences that do NOT contain any specific and
verifiable propositions :
- By prioritizing ethical considerations , companies can ensure that their innovations are not only groundbreaking but also socially responsible
- Technological progress should be inclusive
- Leveraging advanced technologies is essential for maximizing productivity
- Networking events can be crucial in shaping the paths of young entrepreneurs
and providing them with valuable connections
- AI could lead to advancements in healthcare
- This implies that John Smith is a courageous person
- It’s given me a good sense of how clubs actually function behind the scenes—budgeting, event planning, 
  a lot of last-minute fixing—and how to collaborate across different teams. 
- I’m also in that very relatable phase of trying to juggle it all: learning, working, social life, fitness, and downtime.
- That said, I’ve learned to enjoy the chaos a little and just keep showing up.


Here are some examples of sentences that likely contain a specific and
verifiable proposition and how they can be rewritten to only include verifiable
information and it should be labeled (Preference, Property, Claims, Events):
- I’m a second-year Data Science student at the University of Melbourne, 
  and I like to keep life busy and a little chaotic—in the best way. -> 
  Property: "The author is a second year Data Science student in The University of Melbourne."
- I’m constantly bouncing between writing code (Java, Python, R, and some C thrown in), 
  managing coursework, tutoring high school students (mostly English and Maths), and finding 
  any excuse to bring creativity into my routine. -> 
  Claims: "The author claims to know Java, Python, R and C programming languages."
  Property: "The author is a tutor for high school students in English and Math."
  Preference: "The author prefers a creative environment." 
- For the personality side, I’m an ESFP and I think MBTI has its job done well. ->
  Property: "The author is an ESFP."
- Music is my oxygen (R&B especially—smooth vocals and a solid beat make my world go round), 
  and I’m the kind of person who will randomly break into dance if the playlist hits right. -> 
  Preference: "The author likes R&B."
- Image 1 is a 2D platformer game I made recently for my Object-Oriented Software Development subject. 
  It’s based on Donkey Kong, and I got to design and implement everything from movement logic to   
  collision detection. ->
  Events: "The author made a Donkey Kong game for their Object-Oriented Software Development subject."

Your output must adhere to the following format exactly . Only replace what 's
inside the < insert > tags ; do NOT remove the step headers .
Sentence :
< insert >
4 - step stream of consciousness thought process (
    1. reflect on criteria at a high-level -> 
    2. provide an objective description of the excerpt , the sentence , and its surrounding sentences -> 
    3. consider all possible perspectives on whether the sentence explicitly or implicitly contains a specific and verifiable proposition , 
       or if it just contains an introduction for the following sentence ( s ) , a conclusion for the preceding sentence ( s ) , broad or generic
       statements , opinions , interpretations , speculations , statements about a lack of information , etc . -> 
    4. identify if the sentence can be broken down and identify if each statement is a preference, properties, claims -> 
    5. or events only if it contains a specific and verifiable proposition : reflect on whether any changes are needed to ensure 
       that the entire sentence only contains verifiable information 
    ) :
< insert >
Final submission:
< insert 'Contains a specific and verifiable proposition ' or 'Does NOT contain a specific and verifiable proposition '>
Sentence with only verifiable information :
< insert changed sentence , or 'remains unchanged ' if no changes , or 'None ' if the
sentence does NOT contain a specific and verifiable proposition >