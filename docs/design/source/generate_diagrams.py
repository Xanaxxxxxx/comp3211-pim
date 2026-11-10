"""Rebuild the four design figures and PDF; optional documentation tooling only.

Requires reportlab, pypdf and pypdfium2. These are NOT application dependencies.
Run with a Python environment containing those packages:
    python docs/design/source/generate_diagrams.py
"""
from pathlib import Path
import ast
import math
import tempfile
from html import escape

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.colors import HexColor, white
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from reportlab.lib.styles import ParagraphStyle
from pypdf import PdfReader, PdfWriter
import pypdfium2 as pdfium

ROOT = Path(__file__).resolve().parents[3]
DEST = ROOT / 'docs' / 'design'
W, H = 1600, 1131
PAGE = landscape(A3)
INK = '#17283b'
BLUE = '#254f78'
MUTED = '#50657a'
BORDER = '#a5b5c5'
LIGHT = '#f1f5f9'
GREEN = '#e9f4ef'
CREAM = '#fcf5e7'
WHITE = '#ffffff'
SOURCES = ['model/records.py', 'model/manager.py', 'model/criteria.py',
           'model/storage.py', 'model/errors.py', 'controller/commands.py',
           'view/terminal.py', 'main.py']

FIGURES = [
    ('01_architecture', 'System architecture',
     'MVC separation with a command-line entry point and file persistence',
     'The program uses an MVC-style separation: main.py owns terminal I/O, Controller interprets commands, '
     'the view formats records, and model owns records, validation, search and persistence. '
     'This keeps domain operations testable without terminal input. Controller requests formatted text and returns '
     'a CommandResult; main.py prints it. The model does not call the view or controller. Saving/loading is explicit: '
     'storage writes or reads the complete collection as UTF-8 JSON in a .pim file. Startup --file loading also occurs '
     'in main.py. Arrows show calls/data requests; dashed arrows show returned values or output.'),
    ('02_record_classes', 'Record and persistence classes',
     'Typed immutable records, collection ownership and validated file snapshots',
     'PIM owns zero or more Record instances indexed by stable IDs. Note, Task, Event and Contact inherit id, '
     'to_dict() and updated() from Record; each fixes its class-level kind value and adds required fields. '
     'Dataclass constructors are generated from these fields. Updates use dataclasses.replace, which invokes '
     'validation before the collection replaces its reference. All times normalize to Hong Kong (+08:00); '
     'an Event additionally requires alarm <= start. Storage functions operate on PIM snapshots, with atomic '
     'replacement on save and complete reconstruction/validation on load. The composition diamond denotes '
     'collection ownership, not immediate destruction: callers can retain immutable record references.'),
    ('03_search_control_classes', 'Search and control classes',
     'Expression trees, node references and command coordination',
     'Parser builds Predicate, Negation and Junction objects with precedence parentheses, !, &&, then ||. '
     'Each node implements matches(record), but there is no shared interface or superclass in the Python source. '
     'Criterion is only a documentation alias for the union of those three types. Negation references one '
     'criterion; Junction references multiple criteria and short-circuits evaluation. PIM.search calls '
     'parse_criteria and evaluates the resulting tree against its records. Controller owns a PIM and an unsaved-change '
     'flag, uses view formatting functions, and returns an immutable CommandResult. Solid arrows indicate held '
     'references; dashed arrows indicate calls, object creation or returned values.'),
    ('04_search_update_sequence', 'Search then update sequence',
     'Example: find a task, then revise its description by the returned ID',
     'Assume task ID 2 already exists. The user first searches for tasks whose description contains project. '
     'The parser creates a Junction containing two Predicates; PIM evaluates it for each record and the view '
     'formats the matches. After seeing ID 2, the user issues a separate update command. PIM retrieves the '
     'record, creates a validated replacement through Record.updated, and commits it only after validation succeeds. '
     'Controller sets dirty to True and returns formatted confirmation. The sequence stops before save: '
     'the change is in memory and requires an explicit save command to persist. Expected errors are caught '
     'by run_session and shown on stderr; invalid updates leave the original record unchanged.')
]


def wrap(text, font, size, width):
    lines = []
    for paragraph in text.split('\n'):
        current = ''
        for word in paragraph.split():
            candidate = (current + ' ' + word).strip()
            if stringWidth(candidate, font, size) > width and current:
                lines.append(current)
                current = word
            else:
                current = candidate
        lines.append(current)
    return lines


class Drawing:
    def __init__(self, c):
        self.c = c

    def text(self, x, y, text, size=17, font='Helvetica', color=INK, width=None, leading=None):
        c = self.c
        c.setFont(font, size)
        c.setFillColor(HexColor(color))
        lines = wrap(text, font, size, width) if width else text.split('\n')
        for i, line in enumerate(lines):
            if width:
                assert stringWidth(line, font, size) <= width + 1, (line, width)
            c.drawString(x, H-y-size-i*(leading or size*1.3), line)
        return len(lines)*(leading or size*1.3)

    def rect(self, x, y, w, h, fill=WHITE, stroke=BORDER, dashed=False):
        c=self.c
        c.setFillColor(HexColor(fill))
        c.setStrokeColor(HexColor(stroke))
        c.setLineWidth(1.5)
        c.setDash(6,4) if dashed else c.setDash()
        c.rect(x,H-y-h,w,h,fill=1,stroke=1)
        c.setDash()

    def line(self, points, dashed=False, color=MUTED, arrow=False, triangle=False, diamond=False):
        c=self.c
        c.setStrokeColor(HexColor(color))
        c.setFillColor(HexColor(color))
        c.setLineWidth(1.8)
        c.setDash(7,5) if dashed else c.setDash()
        p=c.beginPath();p.moveTo(points[0][0],H-points[0][1])
        for x,y in points[1:]:p.lineTo(x,H-y)
        c.drawPath(p)
        c.setDash()
        if arrow or triangle:
            x,y=points[-1]; px,py=points[-2]
            angle=math.atan2(y-py,x-px)
            length=16 if triangle else 11
            spread=8 if triangle else 5
            bx=x-length*math.cos(angle);by=y-length*math.sin(angle)
            vertices=[(x,y),(bx-spread*math.sin(angle),by+spread*math.cos(angle)),
                      (bx+spread*math.sin(angle),by-spread*math.cos(angle))]
            q=c.beginPath();q.moveTo(vertices[0][0],H-vertices[0][1])
            for vx,vy in vertices[1:]:q.lineTo(vx,H-vy)
            q.close()
            c.setFillColor(white if triangle else HexColor(color))
            c.drawPath(q,fill=1,stroke=1)
        if diamond:
            x,y=points[0];nx,ny=points[1]
            angle=math.atan2(ny-y,nx-x)
            vx,vy=math.cos(angle),math.sin(angle)
            verts=[(x,y),(x+9*vx-5*vy,y+9*vy+5*vx),(x+18*vx,y+18*vy),(x+9*vx+5*vy,y+9*vy-5*vx)]
            q=c.beginPath();q.moveTo(verts[0][0],H-verts[0][1])
            for a,b in verts[1:]:q.lineTo(a,H-b)
            q.close();c.setFillColor(HexColor(INK));c.drawPath(q,fill=1,stroke=1)

    def label(self,x,y,text,width=300):
        lines=wrap(text,'Helvetica',15,width)
        self.rect(x-5,y-2,width+10,len(lines)*19+4,fill=WHITE,stroke=WHITE)
        self.text(x,y,text,size=15,width=width,leading=19)

    def module(self,x,y,w,h,title,body,fill=LIGHT):
        self.rect(x,y,w,h,fill)
        self.text(x+18,y+13,title,20,'Helvetica-Bold',width=w-36)
        self.text(x+18,y+49,body,17,width=w-36,leading=24)

    def cls(self,x,y,w,title,sections,fill=WHITE,size=15):
        h=43 + sum(14 + 21*len(section) for section in sections)
        self.rect(x,y,w,h,fill)
        self.rect(x,y,w,43,fill=LIGHT)
        self.text(x+14,y+10,title,19,'Helvetica-Bold',width=w-28)
        top=y+43
        for index,section in enumerate(sections):
            if index:self.line([(x,top),(x+w,top)],color=BORDER)
            for n,row in enumerate(section):
                self.text(x+13,top+7+21*n,row,size,'Courier',width=w-26,leading=20)
            top += 14+21*len(section)
        return h

    def header(self,index):
        slug,title,subtitle,_=FIGURES[index]
        self.text(55,28,f'{index+1:02d}  {title}',32,'Helvetica-Bold')
        self.text(55,75,subtitle,18,color=MUTED)

    def bottom(self,index):
        self.line([(55,971),(1545,971)],color=BORDER)
        self.text(55,988,'Explanation',18,'Helvetica-Bold')
        height=self.text(200,985,FIGURES[index][3],16,width=1340,leading=21)
        assert height <= 110, height
        self.text(55,1100,'COMP3211 PIM | Based on implemented source | Symbols: + public, # protected by convention',13,color=MUTED)
        self.text(1460,1100,f'Figure {index+1}',13,color=MUTED)


def architecture(d):
    d.module(55,175,220,110,'User','Interactive terminal\nor UTF-8 script',CREAM)
    d.module(365,145,375,160,'Entry point | main.py','main() / run_session()\nRead input; print output\nCatch PIMError -> stderr')
    d.module(365,430,375,160,'Controller','controller.commands\nParse commands; call model\nTrack unsaved changes')
    d.module(940,145,500,145,'View | view.terminal','HELP, format_record(), format_records()\nReturn strings; no terminal I/O')
    d.rect(890,360,655,540,fill=WHITE,dashed=True)
    d.text(910,373,'Model package',22,'Helvetica-Bold')
    d.module(940,425,500,100,'Collection | model.manager','PIM: CRUD, search, snapshots',GREEN)
    d.module(940,590,240,135,'model.criteria','Parse expressions\nEvaluate criteria',GREEN)
    d.module(1210,590,230,135,'model.records','Typed PIRs\nField validation',GREEN)
    d.module(940,790,500,85,'model.storage','save() / load(): validated persistence',GREEN)
    d.module(365,785,375,100,'.pim file','Version 1 UTF-8 JSON\nRecords plus next_id',CREAM)
    d.line([(275,205),(365,205)],arrow=True);d.label(285,177,'input',65)
    d.line([(365,267),(275,267)],dashed=True,arrow=True);d.label(280,290,'printed output',120)
    d.line([(485,305),(485,430)],arrow=True);d.label(500,326,'execute(line)',170)
    d.line([(655,430),(655,305)],dashed=True,arrow=True);d.label(668,360,'CommandResult',175)
    d.line([(740,475),(940,475)],arrow=True);d.label(756,445,'CRUD / search',155)
    d.line([(740,530),(810,530),(810,220),(940,220)],arrow=True);d.label(815,300,'format',65)
    d.line([(1060,525),(1060,590)],arrow=True);d.label(945,547,'parse / match',110)
    d.line([(1325,525),(1325,590)],arrow=True);d.label(1340,550,'create / update',150)
    d.line([(740,570),(850,570),(850,835),(940,835)],arrow=True);d.label(760,650,'save / load',90)
    d.line([(940,855),(740,855)],arrow=True);d.label(755,867,'write / read',135)
    d.line([(1440,830),(1500,830),(1500,475),(1440,475)],arrow=True)
    d.label(1450,735,'snapshot /\nrebuild PIM',90)
    d.text(55,940,'PIMError: ValidationError, RecordNotFound, CriteriaError, StorageError. Startup --file calls model.load() directly.',16,color=MUTED)


def records(d):
    d.cls(55,135,650,'PIM | model.manager',[
        ['# _records: dict[int, Record]','# _next_id: int','+ next_id: int {read-only property}'],
        ['+ __init__()','+ create(kind: str, /, **data) -> Record','+ get(record_id: int) -> Record','+ all() -> tuple[Record, ...]',
         '+ update(record_id: int, /, **changes) -> Record','+ delete(record_id: int) -> Record',
         '+ search(expression: str) -> tuple[Record, ...]','+ snapshot() -> dict','+ from_snapshot(snapshot: object) -> PIM {class}']])
    d.cls(930,135,615,'Record | model.records {frozen dataclass}',[
        ['+ id: int','+ kind: ClassVar[str]'],['+ to_dict() -> dict','+ updated(changes: dict) -> Record']])
    d.line([(705,225),(930,225)],diamond=True)
    d.label(750,185,'owns / indexes',140)
    d.text(714,235,'1',15);d.text(884,235,'0..*',15)
    d.text(940,350,'Generated constructors take the declared fields, including id.\nThe subclasses inherit Record operations; kind is class-level.\nAll record instances are immutable after validation.',17,width=590,leading=25)
    positions=[(55,'Note',['+ text: str','+ kind = "note"']),
               (440,'Task',['+ description: str','+ deadline: datetime','+ kind = "task"']),
               (825,'Event',['+ description: str','+ start: datetime','+ alarm: datetime','+ kind = "event"']),
               (1210,'Contact',['+ name: str','+ address: str','+ mobile: str','+ kind = "contact"'])]
    d.line([(222,505),(1500,505)],color=MUTED)
    d.line([(1500,505),(1500,290)],triangle=True)
    d.label(1375,458,'inherits',95)
    for x,title,attrs in positions:
        d.cls(x,550,335,title,[attrs],size=15)
        d.line([(x+167,550),(x+167,505)])
    d.module(55,790,720,160,'Functions | model.records',
             'make_record(kind: str, record_id: int, data: dict) -> Record\n'
             'parse_time(value: str | datetime) -> datetime\n'
             'require_text(value: object, label: str) -> None\n'
             'require_id(value: object) -> None')
    d.module(825,790,720,160,'Functions | model.storage',
             'save(pim: PIM, path: str | Path) -> None\n'
             'load(path: str | Path) -> PIM\n'
             'pim_path(path: str | Path) -> Path\n'
             'unique_object(pairs: list) -> dict')
    d.text(55,750,'Hollow triangle: inheritance. Filled diamond: collection ownership. ValidationError guards construction and updates.',16,color=MUTED)


def search_control(d):
    d.cls(55,130,550,'Parser | model.criteria',[
        ['+ tokens: list[tuple[str, bool]]','+ position: int'],
        ['+ __init__(expression: str)', '+ accept(token: str) -> bool','+ take() -> tuple[str, bool]',
         '+ parse() -> Criterion [inferred]','+ expression(depth: int) -> Criterion [inferred]',
         '+ conjunction(depth: int) -> Criterion [inferred]','+ unary(depth: int) -> Criterion [inferred]',
         '+ predicate() -> Predicate']])
    d.cls(1010,130,535,'Predicate {frozen dataclass}',[
        ['+ field: str','+ operator: str','+ value: str | datetime'],['+ matches(record: Record) -> bool']])
    d.cls(1010,380,535,'Negation {frozen dataclass}',[
        ['+ operand: object'],['+ matches(record: Record) -> bool']])
    d.cls(1010,610,535,'Junction {frozen dataclass}',[
        ['+ operator: str','+ operands: tuple'],['+ matches(record: Record) -> bool']])
    d.cls(55,595,550,'Controller | controller.commands',[
        ['+ pim: PIM','+ dirty: bool'],['+ __init__(pim: PIM | None = None)','+ execute(line: str) -> CommandResult']])
    d.cls(55,825,550,'CommandResult {frozen dataclass}',[
        ['+ message: str = ""','+ exit_requested: bool = False']])
    d.module(660,555,275,110,'parse_criteria()','expression: str\n-> Criterion [inferred]')
    d.module(660,700,275,85,'PIM [Figure 2]','search() / CRUD operations',GREEN)
    d.module(660,850,275,90,'view.terminal','format_record(s) -> str')
    d.module(1010,850,535,90,'Criterion {documentation alias only}',
             'Predicate | Negation | Junction; not a source class',CREAM)
    d.line([(605,265),(965,265)],dashed=True)
    d.line([(965,218),(965,665)],dashed=True)
    for target_y in (218,444,665):
        d.line([(965,target_y),(1010,target_y)],dashed=True,arrow=True)
    d.label(745,226,'creates nodes',150)
    d.line([(795,555),(795,500),(570,500),(570,411)],dashed=True,arrow=True)
    d.label(620,495,'Parser(...).parse()',210)
    d.line([(795,700),(795,665)],dashed=True,arrow=True)
    d.label(807,673,'calls',65)
    d.line([(605,730),(660,730)],arrow=True)
    d.line([(605,690),(630,690),(630,888),(660,888)],dashed=True,arrow=True)
    d.line([(325,750),(325,825)],dashed=True,arrow=True);d.label(340,786,'returns',85)
    d.line([(1545,445),(1570,445),(1570,878),(1545,878)],arrow=True)
    d.line([(1545,700),(1590,700),(1590,914),(1545,914)],arrow=True)
    d.text(1440,555,'1 operand',14,color=MUTED)
    d.text(1390,795,'2..* parser-built operands',14,color=MUTED)
    d.text(55,945,'Parser / criterion return types marked [inferred] are documentation types; tokens and position are inferred from assignments.',15,color=MUTED)


def sequence_full(d):
    # Compact chronological version retains all important calls and returns.
    xs=[120,360,620,880,1150,1440]
    heads=['User','main.run_session','Controller','PIM','model.criteria','Record / Task']
    for x,name in zip(xs,heads):
        d.rect(x-105,125,210,50,fill=LIGHT)
        d.text(x-94,138,name,16,'Helvetica-Bold')
        d.line([(x,175),(x,947)],dashed=True,color=BORDER)
    def msg(a,b,y,label,ret=False,size=14):
        d.line([(xs[a],y),(xs[b],y)],dashed=ret,arrow=True,color=BLUE if not ret else MUTED)
        textw=stringWidth(label,'Helvetica',size)
        center=(xs[a]+xs[b])/2
        d.rect(center-textw/2-4,y-22,textw+8,20,fill=WHITE,stroke=WHITE)
        d.text(center-textw/2,y-21,label,size)
    # One line per interaction; only intra-component parser calls are summarized.
    msg(0,1,210,'search type=task && ...')
    msg(1,2,250,'execute(search_line)')
    msg(2,3,290,'search(expression)')
    msg(3,4,330,'parse_criteria(expression)')
    d.text(1170,341,'Parser builds Junction of two Predicates',14,width=370)
    msg(4,3,395,'criterion tree',True)
    msg(3,4,440,'loop each record: criterion.matches(record)')
    msg(4,3,480,'bool; compare type and description',True)
    msg(3,2,520,'matching records',True)
    d.text(650,532,'format_records(matches)',14,color=MUTED)
    msg(2,1,575,'CommandResult(message)',True)
    msg(1,0,615,'print matches; user sees ID 2',True)
    msg(0,1,665,'update 2 description="Revised"')
    msg(1,2,705,'execute(update_line)')
    msg(2,3,745,'update(2, description="Revised")')
    msg(3,5,790,'get(2).updated(changes): dataclasses.replace + validation')
    msg(5,3,835,'validated replacement record',True)
    d.text(890,847,'_records[2] = replacement',14,color=MUTED)
    msg(3,2,887,'updated Record',True)
    d.text(650,898,'dirty = True; format_record(record)',14,color=MUTED)
    msg(2,1,930,'CommandResult("Updated ...")',True)
    msg(1,0,960,'print confirmation',True)


RAISES = {
 'Record.updated': 'ValidationError', 'Record.__post_init__': 'ValidationError',
 'Event.__post_init__': 'ValidationError', 'parse_time': 'ValidationError',
 'require_text': 'ValidationError', 'require_id': 'ValidationError', 'make_record': 'ValidationError',
 'PIM.create': 'ValidationError', 'PIM.get': 'ValidationError; RecordNotFound',
 'PIM.update': 'ValidationError; RecordNotFound', 'PIM.delete': 'ValidationError; RecordNotFound',
 'PIM.search': 'CriteriaError', 'PIM.from_snapshot': 'ValidationError',
 'Parser.__init__': 'CriteriaError', 'Parser.take': 'CriteriaError',
 'Parser.parse': 'CriteriaError', 'Parser.expression': 'CriteriaError',
 'Parser.conjunction': 'CriteriaError', 'Parser.unary': 'CriteriaError', 'Parser.predicate': 'CriteriaError',
 'parse_criteria': 'CriteriaError', 'pim_path': 'StorageError', 'save': 'StorageError*',
 'unique_object': 'ValidationError', 'load': 'StorageError',
 'parse_id': 'ValidationError', 'parse_fields': 'ValidationError',
 'Controller.execute': 'PIMError subclasses; see called operation',
 'main': 'SystemExit(2) for invalid startup arguments',
}
INFERRED = {'Parser.parse':'Criterion','Parser.expression':'Criterion','Parser.conjunction':'Criterion',
            'Parser.unary':'Criterion','parse_criteria':'Criterion'}
PURPOSE = {
 'Record.to_dict':'Serialize all fields and type; times become ISO 8601 strings.',
 'Record.updated':'Validate and return a replacement; the original is immutable.',
 'PIM.__init__':'Start an empty record collection and ID allocator.',
 'PIM.next_id':'Read-only property exposing the next unused ID.',
 'PIM.create':'Validate data, store a record and increment next_id only on success.',
 'PIM.get':'Validate the ID and retrieve its immutable record.',
 'PIM.all':'Return records ordered by ID.',
 'PIM.update':'Retrieve, validate replacement, then replace the stored reference.',
 'PIM.delete':'Remove one record and return it; do not reuse its ID.',
 'PIM.search':'Compile expression and evaluate it against all records.',
 'PIM.snapshot':'Return a detached versioned serializable dictionary.',
 'PIM.from_snapshot':'Class method reconstructing a validated collection.',
 'Predicate.matches':'Evaluate type equality, case-insensitive substring, or time comparison.',
 'Negation.matches':'Invert one child result.',
 'Junction.matches':'Evaluate child criteria with short-circuit all/any.',
 'Parser.__init__':'Tokenize input and enforce length/quoting rules.',
 'Parser.accept':'Consume one matching unquoted token; otherwise leave position unchanged.',
 'Parser.take':'Consume and return the next token.',
 'Parser.parse':'Parse the full expression and reject trailing tokens.',
 'Parser.expression':'Parse disjunctions (lowest precedence).',
 'Parser.conjunction':'Parse conjunctions.',
 'Parser.unary':'Parse negation/parentheses and enforce nesting limit.',
 'Parser.predicate':'Validate field/operator/value and normalize time literals.',
 'parse_criteria':'Create Parser(expression), then return parse().',
 'save':'Write snapshot to a temporary file, flush/fsync, then os.replace.',
 'load':'Decode JSON and return PIM.from_snapshot only after full validation.',
 'unique_object':'Reject duplicate JSON keys when decoding objects.',
 'pim_path':'Expand user path and require .pim extension (case-insensitive).',
 'make_record':'Validate record type and exact required fields, then construct it.',
 'parse_time':'Parse datetime or ISO text, require date/time, normalize to +08:00.',
 'require_text':'Require a non-whitespace string without changing stored text.',
 'require_id':'Require a positive int; reject bool.',
 'Controller.__init__':'Use supplied PIM or create one; start with dirty=False.',
 'Controller.execute':'Dispatch a command; track dirty; format results; guard load/quit.',
 'parse_id':'Convert command text to a positive integer.',
 'parse_fields':'Parse field=value arguments and reject duplicates.',
 'format_record':'Format every field with unambiguous JSON-quoted values.',
 'format_records':'Format the count followed by all detailed records.',
 'run_session':'Read commands; print messages; catch PIMError; return process status.',
 'main':'Parse startup options, load optional file and launch a session.',
 'Record.__post_init__':'Validate id/text fields and normalize datetime fields.',
 'Event.__post_init__':'Run inherited checks and reject alarm after start.',
}


def appendix(path):
    body=ParagraphStyle('body',fontName='Helvetica',fontSize=10,leading=14,spaceAfter=8)
    cell=ParagraphStyle('cell',fontName='Helvetica',fontSize=9,leading=12)
    heading=ParagraphStyle('heading',fontName='Helvetica-Bold',fontSize=17,leading=22,spaceBefore=15,spaceAfter=10,keepWithNext=True)
    title=ParagraphStyle('title',fontName='Helvetica-Bold',fontSize=24,leading=30,spaceAfter=14)
    story=[Paragraph('Design notes and API reference',title),
        Paragraph('These notes describe the implemented system, not a proposed redesign. '+
        'The first four pages contain the four requested figures and their English explanations. '+
        'This appendix supplies method/function parameters, return types and expected exceptions.',body),
        Paragraph('Notation and implementation details',heading),
        Paragraph('A hollow triangle means inheritance; a filled diamond indicates collection ownership. '+
        'A solid directed association represents a retained reference, while dashed dependency arrows represent calls or creation. '+
        'Sequence arrows are calls/actions and dashed arrows are replies. Self is omitted from method signatures. '+
        'A slash marks positional-only parameters; **data and **changes collect keyword fields. '+
        'ClassVar marks class-level data. The # symbol means an underscore-prefixed attribute, protected only by convention. '+
        'For **data and **changes, keyword names are the type-specific fields in Figure 2; text values are str, '+
        'while time fields accept str | datetime and are stored as normalized datetime objects.',body),
        Paragraph('Record, Note, Task, Event, Contact, Predicate, Negation, Junction and CommandResult are frozen dataclasses. '+
        'Their constructors are generated from the fields shown in Figures 2 and 3. Record and all Record subclass construction '+
        'can raise ValidationError through __post_init__. Other frozen dataclasses do not independently validate constructor arguments. '+
        'Parser tokens/position and return types labelled inferred are documentation types inferred from assignments or returns. '+
        'Criterion abbreviates Predicate | Negation | Junction and is not defined as a class or alias in the source.',body),
        Paragraph('Errors and state guarantees',heading),
        Paragraph('PIMError extends Exception. ValidationError, RecordNotFound, CriteriaError and StorageError directly extend PIMError. '+
        'The CLI catches PIMError and reports the message; lower-level validation errors in file decoding are wrapped as StorageError. '+
        'Validation failure during create does not consume an ID; failure during update leaves the stored record intact. '+
        'Load validates a new collection before replacing the active one. Save uses os.replace after a successful temporary write. '+
        '* save normally wraps OSError/ValueError as StorageError, but an OSError from the finally-block temporary-file cleanup '+
        'can propagate directly; this is an implementation detail, not a guarantee that all filesystem errors are wrapped.',body),
        Paragraph('Sequence example and scope',heading),
        Paragraph('Figure 4 assumes task ID 2 exists. The full search command is '+
        '<font name="Courier">search type=task &amp;&amp; description contains &quot;project&quot;</font>. '+
        'The subsequent command is <font name="Courier">update 2 description=&quot;Revised&quot;</font>. '+
        'The criteria participant represents the module and its parser/evaluation objects; Record/Task is the matched task instance. '+
        'Calls internal to one participant, such as Parser.parse and PIM.get, are summarized in labels. '+
        'Formatting functions execute synchronously inside Controller.execute; no separate thread or GUI exists. '+
        'This is the successful path. A malformed expression raises CriteriaError; a missing ID raises RecordNotFound; '+
        'an invalid replacement raises ValidationError. The session reports these errors and continues. '+
        'Persistence is not automatic: the example requires save to write the update to disk.',body)]
    for source in SOURCES:
        tree=ast.parse((ROOT/source).read_text())
        entries=[]
        def collect(node,owner=''):
            for item in node.body:
                if isinstance(item,ast.ClassDef):
                    collect(item,item.name)
                elif isinstance(item,(ast.FunctionDef,ast.AsyncFunctionDef)):
                    name=f'{owner}.{item.name}' if owner else item.name
                    args=ast.unparse(item.args)
                    if owner:
                        args=args.removeprefix('self, ').removeprefix('cls, ')
                        if args in {'self','cls'}:args=''
                    ret=ast.unparse(item.returns) if item.returns else INFERRED.get(name,'None' if item.name in {'__init__','__post_init__'} else '?')
                    suffix=' [inferred]' if not item.returns else ''
                    sig=f'{name}({args}) -> {ret}{suffix}'
                    entries.append((sig,PURPOSE.get(name,'See source implementation.'),RAISES.get(name,'No expected domain exception for valid model inputs')))
        collect(tree)
        if not entries:continue
        story.append(Paragraph(escape(source),heading))
        rows=[[Paragraph('<b>Signature</b>',cell),Paragraph('<b>Responsibility</b>',cell),Paragraph('<b>Expected exceptions / notes</b>',cell)]]
        for sig,purpose,errors in entries:
            rows.append([Paragraph(escape(sig),cell),Paragraph(escape(purpose),cell),Paragraph(escape(errors),cell)])
        table=Table(rows,colWidths=[310,265,175],repeatRows=1,hAlign='LEFT')
        table.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,0),(-1,0),HexColor('#e7eef5')),
            ('ROWBACKGROUNDS',(0,1),(-1,-1),[white,HexColor('#f5f7f9')]),
            ('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),
            ('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8)]))
        story.extend([table,Spacer(1,8)])
    story.extend([Paragraph('Source and acknowledgement',heading),
        Paragraph('Source baseline: commit fcaee3f in Xanaxxxxxx/comp3211-pim. Figures use actual module, class and method names. '+
        'This document and its diagram generation source were prepared with OpenAI Codex assistance. '+
        'The group should acknowledge actual use in its Honour Declaration. The diagrams and explanations support '+
        'the design-document deliverable; they do not replace the group SRS, presentation or declaration.',body)])
    # A4 landscape appendix is comfortable for the signature table.
    from reportlab.lib.pagesizes import A4
    ap=landscape(A4)
    def foot(c,doc):
        c.setFont('Helvetica',9);c.drawString(46,24,'COMP3211 PIM | Design notes and API reference');c.drawRightString(ap[0]-46,24,str(doc.page+4))
    SimpleDocTemplate(str(path),pagesize=ap,leftMargin=46,rightMargin=46,topMargin=38,bottomMargin=45).build(story,onFirstPage=foot,onLaterPages=foot)


def main():
    DEST.mkdir(parents=True,exist_ok=True)
    (DEST/'images').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as temp:
        temp=Path(temp)
        c=canvas.Canvas(str(temp/'figures.pdf'),pagesize=PAGE)
        c.setTitle('PIM design diagrams')
        for index,draw in enumerate([architecture,records,search_control,sequence_full]):
            c.saveState();c.scale(PAGE[0]/W,PAGE[1]/H)
            d=Drawing(c);d.header(index);draw(d);d.bottom(index)
            c.restoreState();c.showPage()
        c.save()
        appendix(temp/'appendix.pdf')
        writer=PdfWriter()
        writer.append(str(temp/'figures.pdf'));writer.append(str(temp/'appendix.pdf'))
        writer.add_metadata({'/Title':'COMP3211 PIM Design Diagrams and Explanations','/Author':'Prepared with OpenAI Codex assistance'})
        output=DEST/'PIM_Design_Diagrams.pdf'
        with output.open('wb') as stream:writer.write(stream)
    notes=['# PIM design explanations', '', 'Source baseline: `fcaee3f`. See the PDF appendix for full API and exception details.', '']
    for i,(slug,title,subtitle,explanation) in enumerate(FIGURES):
        notes.extend([f'## Figure {i+1} {title}', '', explanation, '', f'![{title}](images/{slug}.png)', ''])
    (DEST/'DESIGN_EXPLANATIONS.md').write_text('\n'.join(notes), encoding='utf-8')
    pdf=pdfium.PdfDocument(output)
    for i,(slug,*_) in enumerate(FIGURES):
        im=pdf[i].render(scale=2).to_pil()
        im.save(DEST/'images'/(slug+'.png'))
    print(f'Created {output.name}: {len(pdf)} pages; four PNG figures.')


if __name__=='__main__':main()
