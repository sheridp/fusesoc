import os
from fusesoc.config import Config
from fusesoc import utils
from fusesoc.utils import Launcher, pr_warn, pr_info


class Error(Exception):
    pass


class NoSuchItemError(Error):
    pass


class UnknownSection(Error):
    pass


class Section(object):

    TAG = None

    def __init__(self):
        self.strings = []
        self.lists  = []
        self.export_files = []
        self.warnings = []

    def _add_listitem(self, listitem):
        self.lists += [listitem]
        setattr(self, listitem, [])

    def _add_stringitem(self, s):
        self.strings += [s]
        setattr(self, s, "")

    def export(self):
        return self.export_files

    def load_dict(self, items):
        for item in items:
            if item in self.lists:
                setattr(self, item, items.get(item).split())
            elif item in self.strings:
                setattr(self, item, items.get(item))
            else:
                self.warnings.append(
                        'Unknown item "%(item)s" in section "%(section)s"' % {
                            'item': item, 'section': self.TAG})

    def __str__(self):
        s = ''
        for item in self.lists:
            s += item + ' : ' + ';'.join(getattr(self, item)) + '\n'
        for item in self.strings:
            s += item + ' : ' + getattr(self, item) + '\n'
        return s

class ToolSection(Section):
    def __init__(self):
        super(ToolSection, self).__init__()
        self._add_listitem('depend')

class MainSection(Section):
    TAG = 'main'

    def __init__(self, items=None):
        super(MainSection, self).__init__()

        self._add_stringitem('description')
        self._add_listitem('depend')
        self._add_listitem('simulators')

        if items:
            self.load_dict(items)

class VhdlSection(Section):

    TAG = 'vhdl'

    def __init__(self, items=None):
        super(VhdlSection, self).__init__()

        self._add_listitem('src_files')

        if items:
            self.load_dict(items)
            self.export_files = self.src_files

class VerilogSection(Section):

    TAG = 'verilog'

    def __init__(self, items=None):
        super(VerilogSection, self).__init__()

        self.include_dirs = []
        self.tb_include_dirs = []

        self._add_listitem('src_files')
        self._add_listitem('include_files')
        self._add_listitem('tb_src_files')
        self._add_listitem('tb_private_src_files')
        self._add_listitem('tb_include_files')

        if items:
            self.load_dict(items)
            if self.include_files:
                self.include_dirs  += list(set(map(os.path.dirname, self.include_files)))
            if self.tb_include_files:
                self.tb_include_dirs  += list(set(map(os.path.dirname, self.tb_include_files)))

            self.export_files = self.src_files + self.include_files + self.tb_src_files + self.tb_include_files + self.tb_private_src_files
    def __str__(self):
        s = ""
        if self.src_files:            s += "\nRTL source files :\n {}".format('\n '.join(self.src_files))
        if self.include_files:        s += "\nRTL include files :\n {}".format('\n '.join(self.include_files))
        if self.include_dirs:         s += "\nRTL Include directories :\n {}".format('\n '.join(self.include_dirs))
        if self.tb_src_files:         s += "\nPublic testbench source files :\n {}".format('\n '.join(self.tb_src_files))
        if self.tb_private_src_files: s += "\nPrivate testbench source files :\n {}".format('\n '.join(self.tb_private_src_files))
        if self.tb_include_files:     s += "\nTestbench include files :\n {}".format('\n '.join(self.tb_include_files))
        if self.tb_include_dirs:      s += "\nTestbench include directories :\n {}".format('\n '.join(self.tb_include_dirs))

        return s

class VpiSection(Section):

    TAG = 'vpi'

    def __init__(self, items=None):
        super(VpiSection, self).__init__()

        self.include_dirs = []

        self._add_listitem('src_files')
        self._add_listitem('include_files')
        self._add_listitem('libs')

        if items:
            self.load_dict(items)
            if self.include_files:
                self.include_dirs  += list(set(map(os.path.dirname, self.include_files)))

            self.export_files = self.src_files + self.include_files


class ModelsimSection(ToolSection):

    TAG = 'modelsim'

    def __init__(self, items=None):
        super(ModelsimSection, self).__init__()

        self._add_listitem('vlog_options')
        self._add_listitem('vsim_options')

        if items:
            self.load_dict(items)

class IcarusSection(ToolSection):

    TAG = 'icarus'

    def __init__(self, items=None):
        super(IcarusSection, self).__init__()

        self._add_listitem('iverilog_options')

        if items:
            self.load_dict(items)

    def __str__(self):
        s = ""
        if self.depend: s += "Icarus-specific dependencies : {}".format(' '.join(self.depend))
        if self.iverilog_options: s += "Icarus compile options : {}".format(' '.join(self.iverilog_options))
        return s


class VerilatorSection(ToolSection):

    TAG = 'verilator'

    def __init__(self, items=None):
        super(VerilatorSection, self).__init__()

        self.include_dirs = []
        self.archive = False
        self._object_files = []

        self._add_listitem('verilator_options')
        self._add_listitem('src_files')
        self._add_listitem('include_files')
        self._add_listitem('define_files')
        self._add_listitem('libs')

        self._add_stringitem('tb_toplevel')
        self._add_stringitem('source_type')
        self._add_stringitem('top_module')

        if items:
            self.load_dict(items)
            self.include_dirs  = list(set(map(os.path.dirname, self.include_files)))
            if self.src_files:
                self._object_files = [os.path.splitext(os.path.basename(s))[0]+'.o' for s in self.src_files]
                self.archive = True
                self.export_files = self.src_files + self.include_files


    def __str__(self):
        s = """Verilator options       : {verilator_options}
Testbench source files  : {src_files}
Testbench include files : {include_files}
Testbench define files  : {define_files}
External libraries      : {libs}
Testbench top level     : {tb_toplevel}
Testbench source type   : {source_type}
Verilog top module      : {top_module}
"""
        return s.format(verilator_options=' '.join(self.verilator_options),
                        src_files = ' '.join(self.src_files),
                        include_files=' '.join(self.include_files),
                        define_files=' '.join(self.define_files),
                        libs=' '.join(self.libs),
                        tb_toplevel=self.tb_toplevel,
                        source_type=self.source_type,
                        top_module=self.top_module)

    def build(self, core, sim_root, src_root):
        if self.source_type == 'C' or self.source_type == '':
            self.build_C(core, sim_root, src_root)
        elif self.source_type == 'CPP':
            self.build_CPP(core, sim_root, src_root)
        elif self.source_type == 'systemC':
            self.build_SysC(core, sim_root, src_root)
        else:
            raise Source(self.source_type)

        if self._object_files:
            args = []
            args += ['rvs']
            args += [core+'.a']
            args += self._object_files
            l = Launcher('ar', args,
                     cwd=sim_root)
            if Config().verbose:
                pr_info("  linker working dir: " + sim_root)
                pr_info("  linker command: ar " + ' '.join(args))
            l.run()
            print()

    def build_C(self, core, sim_root, src_root):
        args = ['-c']
        args += ['-std=c99']
        args += ['-I'+src_root]
        args += ['-I'+os.path.join(src_root, core, s) for s in self.include_dirs]
        for src_file in self.src_files:
            pr_info("Compiling " + src_file)
            l = Launcher('gcc',
                     args + [os.path.join(src_root, core, src_file)],
                         cwd=sim_root,
                         stderr = open(os.path.join(sim_root, 'gcc.err.log'),'a'),
                         stdout = open(os.path.join(sim_root, 'gcc.out.log'),'a'))
            if Config().verbose:
                pr_info("  C compilation working dir: " + sim_root)
                pr_info("  C compilation command: gcc " + ' '.join(args) + ' ' + os.path.join(src_root, core, src_file))
            l.run()

    def build_CPP(self, core, sim_root, src_root):
        verilator_root = utils.get_verilator_root()
        if verilator_root is None:
            verilator_root = utils.get_verilator_root()
        args = ['-c']
        args += ['-I'+src_root]
        args += ['-I'+os.path.join(src_root, core, s) for s in self.include_dirs]
        args += ['-I'+os.path.join(verilator_root,'include')]
        args += ['-I'+os.path.join(verilator_root,'include', 'vltstd')]
        for src_file in self.src_files:
            pr_info("Compiling " + src_file)
            l = Launcher('g++', args + [os.path.join(src_root, core, src_file)],
                         cwd=sim_root,
                         stderr = open(os.path.join(sim_root, 'g++.err.log'),'a'))
            if Config().verbose:
                pr_info("  C++ compilation working dir: " + sim_root)
                pr_info("  C++ compilation command: g++ " + ' '.join(args) + ' ' + os.path.join(src_root, core, src_file))
            l.run()

    def build_SysC(self, core, sim_root, src_root):
        verilator_root = utils.get_verilator_root()
        args = ['-I.']
        args += ['-MMD']
        args += ['-I'+src_root]
        args += ['-I'+s for s in self.include_dirs]
        args += ['-Iobj_dir']
        args += ['-I'+os.path.join(verilator_root,'include')]
        args += ['-I'+os.path.join(verilator_root,'include', 'vltstd')]  
        args += ['-DVL_PRINTF=printf']
        args += ['-DVM_TRACE=1']
        args += ['-DVM_COVERAGE=0']
        if os.getenv('SYSTEMC_INCLUDE'):
            args += ['-I'+os.getenv('SYSTEMC_INCLUDE')]
        if os.getenv('SYSTEMC'):
            args += ['-I'+os.path.join(os.getenv('SYSTEMC'),'include')]
        args += ['-Wno-deprecated']
        if os.getenv('SYSTEMC_CXX_FLAGS'):
             args += [os.getenv('SYSTEMC_CXX_FLAGS')]
        args += ['-c']
        args += ['-g']

        for src_file in self.src_files:
            pr_info("Compiling " + src_file)
            l = Launcher('g++', args + [os.path.join(src_root, core, src_file)],
                         cwd=sim_root,
                         stderr = open(os.path.join(sim_root, 'g++.err.log'),'a'))
            if Config().verbose:
                pr_info("  SystemC compilation working dir: " + sim_root)
                pr_info("  SystemC compilation command: g++ " + ' '.join(args) + ' ' + os.path.join(src_root, core, src_file))
            l.run()

class IseSection(ToolSection):

    TAG = 'ise'

    def __init__(self, items=None):
        super(IseSection, self).__init__()

        self._add_listitem('ucf_files')
        self._add_listitem('tcl_files')
        self._add_stringitem('family')
        self._add_stringitem('device')
        self._add_stringitem('package')
        self._add_stringitem('speed')
        self._add_stringitem('top_module')

        if items:
            self.load_dict(items)
            self.export_files = self.ucf_files

class QuartusSection(ToolSection):

    TAG = 'quartus'

    def __init__(self, items=None):
        super(QuartusSection, self).__init__()

        self._add_listitem('qsys_files')
        self._add_listitem('sdc_files')
        self._add_listitem('tcl_files')

        self._add_stringitem('quartus_options')
        self._add_stringitem('family')
        self._add_stringitem('device')
        self._add_stringitem('top_module')

        if items:
            self.load_dict(items)
            self.export_files = self.qsys_files + self.sdc_files


def load_section(config, section_name, name='<unknown>'):
    cls = SECTION_MAP.get(section_name)
    if cls is None:
        return None

    items = config.get_section(section_name)
    section = cls(items)
    if section.warnings:
        for warning in section.warnings:
            pr_warn('Warning: %s in %s' % (warning, name))
    return section


def load_all(config, name='<unknown>'):
    for section_name in config.sections():
        section = load_section(config, section_name, name)
        if section:
            yield section


SECTION_MAP = {}


def _register_subclasses(parent):
    for cls in parent.__subclasses__():
        _register_subclasses(cls)
        if cls.TAG is None:
            continue
        SECTION_MAP[cls.TAG] = cls


_register_subclasses(Section)
