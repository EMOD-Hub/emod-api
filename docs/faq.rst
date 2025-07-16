====
FAQ
====

As you get started with |emod_api|, you may have questions. The most common
questions are answered below. If you are using |EMODPY_s| packages, see
the FAQs from those packages for additional guidance.


I notice that I can import emod_api.campaign and use that as an object. I haven't seen that before.
	Sure. Python modules are a lot like singletons. There's no need to add a
	static class inside that module in many cases. Think of the module (which can
	have variables and methods) as a static class.

Is there a function to write a demographics configuration to disk?
	Yes. The main Demographics class has a function called generate_file(). https://docs.idmod.org/projects/emod-api/en/latest/emod_api.demographics.Demographics.html#emod_api.demographics.Demographics.Demographics.generate_file 

How can I specify mulitiple Individual Property (IP) targets for an intervention?
	The supported ways of formatting IP targers are:
	
	- "key:value"
        - "key=value"
        - "key1:value1,key2:value2"
	- "key1=value1,key2=value2"
	- { "key": "value" }
	- { "key1": "value1", "key2": "value2" }
	- [  { "key1": "value1", "key2": "value2" }, { "key3": "value3", "key4": "value4" } ]
	- [ "key:value" ]
	- [ "key1:value1", "key2:value2" ]
	
        Some other formats will be added as requested.
	
