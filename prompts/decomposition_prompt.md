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
Here are some correct examples that you must pay attention to :
1. Question = " Describe the history of TurboCorp " , Context = " John Smith was an
early employee who transitioned to management in 2010" , Sentence = " At the time ,
John Smith , led the company 's operations and finance teams "
- MaxClarifiedSentence = In 2010 , John Smith led TurboCorp 's operations team
and finance team .
- Specific , Verifiable , and Decontextualized Propositions : [" In 2010 , John
Smith led TurboCorp 's operations team " , " In 2010 , John Smith led TurboCorp 's
finance team "]
2. Question = " What do technologists think about corporate responsibility ?" ,
Context = "[...]## Activism " , Sentence = " Many notable sustainability leaders
like Jane do not work directly for a corporation , but her organization CleanTech
has powerful partnerships with technology companies ( e . g . , MiniMax ) to
significantly improve waste management , demonstrating the power of
collaboration ."
- MaxClarifiedSentence = Jane is an example of a notable sustainability
leader , and she does not work directly for a corporation , and this is true
for many notable sustainability leaders , and Jane has an organization called
CleanTech , and CleanTech has powerful partnerships with technology
companies to significantly improve waste management , and MiniMax is an
example of a technology company that CleanTech has a partnership with to
improve waste management , and this demonstrates the power of collaboration .
- Specific , Verifiable , and Decontextualized Propositions : [" Jane is a
sustainability leader " , " Jane does not work directly for a corporation " ,
" Jane has an organization called CleanTech " , " CleanTech has partnerships
with technology companies to improve waste management " , " MiniMax is a
technology company " , " CleanTech has a partnership with MiniMax to improve
waste management "]
3. Question = " What are the key topics ?" , Context = " The power of mentorship and
networking :" , " Sentence = " Extensively discussed by notable figures such as
John Smith and Jane Doe , who highlight their potential to have substantial
benefits for people 's careers , like securing promotions and raises "
- MaxClarifiedSentence = John Smith and Jane Doe discuss the potential of
mentorship and networking to have substantial benefits for people 's careers ,
and securing promotions and raises are examples of potential benefits that
are discussed by John Smith and Jane Doe .
- Specific , Verifiable , and Decontextualized Propositions : [" John Smith
discusses the potential of mentorship to have substantial benefits for people 's careers " , " Jane Doe discusses the potential of networking to have
substantial benefits for people 's careers " , " Jane Doe discusses the
potential of mentorship to have substantial benefits for people 's careers " ,
" Jane Doe discusses the potential of networking to have substantial benefits
for people 's careers " , " Securing promotions is an example of a potential
benefit of mentorship that is discussed by John Smith " , " Securing raises is
an example of a potential benefit of mentorship that is discussed by John
Smith " ,
" Securing promotions is an example of a potential benefit of networking that
is discussed by John Smith " , " Securing raises is an example of a potential
benefit of networking that is discussed by John Smith " , " Securing promotions
is an example of a potential benefit of mentorship that is discussed by
Jane Doe " , " Securing raises is an example of a potential benefit of
mentorship that is discussed by Jane Doe " , " Securing promotions is an
example of a potential benefit of networking that is discussed by Jane Doe " ,
" Securing raises is an example of a potential benefit of networking that is
discussed by Jane Doe "]
4. Question = " What is the status of global trade relations ?" , Context =
"[...]** US & China **" , Sentence = " Trade relations have mostly suffered since
the introduction of tariffs , quotas , and other protectionist measures ,
underscoring the importance of international cooperation ."
- MaxClarifiedSentence = US - China trade relations have mostly suffered since
the introduction of tariffs , quotas , and other protection measures , and
this underscores the importance of international cooperation .
- Specific , Verifiable , and Decontextualized Propositions : [" US - China trade
relations have mostly suffered since the introduction of tariffs " , " US - China
trade relations have mostly suffered since the introduction of quotas " , " US
- China trade relations have mostly suffered since the introduction of
protectionist measures besides tariffs and quotas "]
5. Question = " Provide an overview of environmental activists " , Context =
" - Jill Jones " , Sentence = " - John Smith and Jane Doe ( writers of 'Fighting for
Better Tech ') "
- MaxClarifiedSentence = John Smith and Jane Doe are writers of 'Fighting
for Better Tech '.
- Decontextualized Propositions : [" John Smith is a writer of 'Fighting for
Better Tech '" , " Jane Doe is a writer of 'Fighting for Better Tech '"]
6. Question = " What are the experts ' opinions on disruptive technologies ?" ,
Context = "[...] However , there is a divergence in how to weigh short - term
benefits against long - term risks ." , Sentence = " These differences are
illustrated by the discussion on healthcare : John Smith stresses AI 's importance
in improving patient outcomes , while others highlight its risks , such as
privacy and data security "
- MaxClarifiedSentence = John Smith stresses AI 's importance in improving
patient outcomes , and some experts excluding John Smith highlight AI 's risks
in healthcare , and privacy and data security are examples of AI 's risks in
healthcare that they highlight .
- Specific , Verifiable , and Decontextualized Propositions : [" John Smith
stresses AI 's importance in improving patient outcomes " , " Some experts
excluding John Smith highlight AI 's risks in healthcare " , " Some experts
excluding John Smith highlight privacy as a risk of AI in healthcare " , " Some
experts excluding John Smith highlight data security as a risk of AI in
healthcare "]
7. Question = " How can startups improve profitability ?" Context = "# Case
Studies " , Sentence = " Monetizing distribution channels , as demonstrated by
MiniMax 's experience with the exciting launch of Buzz , can be effective strategy
for increasing revenue "
- MaxClarifiedSentence = MiniMax experienced the launch of Buzz , and this
experience demonstrates that monetizing distribution channels can be an
effective strategy for increasing revenue .
- Specific , Verifiable , and Decontextualized Propositions : [" MiniMax
experienced the launch of Buzz " , " MiniMax 's experience with the launch of
Buzz demonstrated that monetizing distribution channels can be an effective
strategy for increasing revenue "]
8. Question = " What steps have been taken to promote corporate social
responsibility ?" , Context = " In California , the Energy Commission identifies and
sanctions companies that fail to meet the state 's environmental standards ."
Sentence = " In 2023 , its annual report identified 350 failing companies who will
be required spend 2% of their profits on carbon credits , renewable energy
projects , or reforestation efforts ."
- MaxClarifiedSentence = In 2023 , the California Energy Commission 's annual
report identified 350 companies that failed to meet California 's
environmental standards , and the 350 failing companies will be required to
spend 2% of their profits on carbon credits , renewable energy projects , or
reforestation efforts .
- Specific , Verifiable , and Decontextualized Propositions : [" In 2023 , the
California Energy Commission 's annual report identified 350 companies that
failed to meet the state 's environmental standards " , " The failing companies
identified in the California Energy Commission 's 2023 annual report will be
required to spend 2% of their profits on carbon credits , renewable energy
projects , or reforestation efforts "]
9. Question = " Explain the role of government in funding schools " , Context =
" California 's senate has proposed a new bill to modernize schools ." , Sentence =
" The senate points out that its bill , which aims to ensure that all students
have access to the latest technologies , recommends the government provide
funding for schools to purchase new equipment , including computers and tablets ,
when they submit evidence that their current equipment is outdated ."
- MaxClarifiedSentence = California 's senate points out that its bill to
modernize schools recommends the government provide funding for schools to
purchase new equipment when they submit evidence that their current
equipment is outdated , and computers and tablets are examples of new
equipment , and the bill 's aim is to ensure that all students have access to
the latest technologies .
- Specific , Verifiable , and Decontextualized Propositions : [" California 's
senate 's bill to modernize schools recommends the government provide funding
for schools to purchase new equipment when they submit evidence that their
current equipment is outdated " , " Computers are examples of new equipment
that the California senate 's bill to modernize schools recommends the
government provide funding for " , " Tablets are examples of new equipment that
the California senate 's bill to modernize schools recommends the government
provide funding for " , " The aim of the California senate 's bill to modernize
schools is to ensure that all students have access to the latest
technologies "]
10. Question = " What companies are profiled ?" , Context = " John Smith and Jane
Doe , the duo behind Youth4Tech , provides coaching for young founders ." , Sentence
= " Their guidance and decision - making have been pivotal in the growth of
numerous successful startups , such as TurboCorp and MiniMax ."
- MaxClarifiedSentence = The guidance and decision - making of John Smith and
Jane Doe have been pivotal in the growth of successful startups , and
TurboCorp and MiniMax are examples of successful startups that John Smith
and Jane Doe 's guidance and decision - making have been pivotal in .
- Specific , Verifiable , and Decontextualized Propositions : [" John Smith 's
guidance has been pivotal in the growth of successful startups " ,
" John Smith 's decision - making has been pivotal in the growth of successful
startups " , " Jane Doe 's guidance has been pivotal in the growth of successful
startups " , " Jane Doe 's decision - making has been pivotal in the growth of
successful startups " , " TurboCorp is a successful startup " , " MiniMax is a
successful startup " , " John Smith 's guidance has been pivotal in the growth
of TurboCorp " , " John Smith 's decision - making has been pivotal in the growth
of TurboCorp " , " John Smith 's guidance has been pivotal in the growth of
MiniMax " , " John Smith 's decision - making has been pivotal in the growth of
MiniMax " , " Jane Doe 's guidance has been pivotal in the growth of TurboCorp " ,
" Jane Doe 's decision - making has been pivotal in the growth of TurboCorp " ,
" Jane Doe 's guidance has been pivotal in the growth of MiniMax " , " Jane Doe 's
decision - making has been pivotal in the growth of MiniMax "]
First , print " Sentence :" followed by the sentence , Then print " Referential terms
whose referents must be clarified ( e . g . , " other ") :" followed by an overview of
all terms in the sentence that explicitly or implicitly refer to other terms in
the sentence , ( e . g . , " other " in " the Department of Education , the Department of
Defense , and other agencies " refers to the Department of Education and the
Department of Defense ; " earlier " in " unlike the 2023 annual report , earlier
reports " refers to the 2023 annual report ) or None if there are no referential terms , Then print " MaxClarifiedSentence :" which articulates discrete units of
information made by the sentence and clarifies referents , Then print " The range
of the possible number of propositions ( with some margin for variation ) is :"
followed by X - Y where X can be 0 or greater and X and Y must be different
integers . Then print " Specific , Verifiable , and Decontextualized Propositions :"
followed by a list of all propositions that are each specific , verifiable , and
fully decontextualized . Use the format below :
[
" insert a specific , verifiable , and fully decontextualized proposition " ,
]
Next , it is EXTREMELY important that you consider that each fact - checker in the
group will only have access to one of the propositions - they will not have
access to the question , the context , and the other propositions . Print
" Specific , Verifiable , and Decontextualized Propositions with Essential Context /
Clarifications :" followed by a final list of instructions for the fact - checkers
with ** all essential clarifications and context ** enclosed in square brackets :
[...]. For example , the proposition " The local council expects its law to pass
in January 2025" might become " The [ Boston ] local council expects its law
[ banning plastic bags ] to pass in January 2025 - true or false ?"; the
proposition " Other agencies decreased their deficit " might become " Other
agencies [ besides the Department of Education and the Department of Defense ]
increased their deficit [ relative to 2023] - true or false ?"; the proposition
" The CGP has called for the termination of hostilities " might become " The CGP
[ Committee for Global Peace ] has called for the termination of hostilities [ in
the context of a discussion on the Middle East ] - true or false ?". Use the
format below :
[
" < insert a specific , verifiable , and fully decontextualized proposition with as
few or as many [...] as needed > - true or false ?" ,
]