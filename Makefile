all:
	$(MAKE) -C batteries_uncertain1.mcdplib
	$(MAKE) -C batteries_uncertain2.mcdplib
	$(MAKE) -C batteries_uncertain3.mcdplib
	$(MAKE) -C droneD_complete_templates.mcdplib

autogen:
	$(MAKE) -C batteries_uncertain1.mcdplib   autogen
	$(MAKE) -C batteries_uncertain2.mcdplib   autogen
	$(MAKE) -C batteries_uncertain3.mcdplib   autogen
	$(MAKE) -C droneD_complete_templates.mcdplib autogen

clean:
	$(MAKE) -C batteries_uncertain1.mcdplib  clean
	$(MAKE) -C batteries_uncertain2.mcdplib clean
	$(MAKE) -C batteries_uncertain3.mcdplib  clean
	$(MAKE) -C droneD_complete_templates.mcdplib clean
