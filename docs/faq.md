# FAQ

Several common questions are answered below. If using the [emodpy][emodpy] packages, be sure to read the FAQs from those packages for additional guidance.

**I notice that I can import emod_api.campaign and use that as an object.**
: Python modules are a lot like singletons. The module (which can have variables and methods) can be used as a static class.

**Is there a function to write a demographics configuration to disk?**
: Yes. The main Demographics class has a function called generate_file(). https://docs.idmod.org/projects/emod-api/en/latest/emod_api.demographics.Demographics.html#emod_api.demographics.Demographics.Demographics.generate_file 


**How can I specify mulitiple Individual Property (IP) targets for an intervention?**
: The supported ways of formatting IP targers are:
: `"key:value"`
: `"key=value"`
: `"key1:value1,key2:value2"`
: `"key1=value1,key2=value2"`
: `{ "key": "value" }`
: `{ "key1": "value1", "key2": "value2" }`
: `[ { "key1": "value1", "key2": "value2" }, { "key3": "value3 } ]`
: `[ "key:value" ]`
: `[ "key1:value1", "key2:value2" ]`

{%
    include-markdown "bib.md"
%}
