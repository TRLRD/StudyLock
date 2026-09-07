"""100 original A Level chemistry practice questions for StudyLock testing."""

def questions():
    out=[]
    def add(i,q,c,a,t,d='Normal'):
        out.append({'id':f'al-{i:03d}','question':q,'choices':c,'answers':[a],'topic':t,'difficulty':d,'curriculum':'gcse','subject':'Chemistry','qualification_stage':'A Level','exam_board':'StudyLock Original','paper_reference':'Original practice'})
    elements=[('lithium','Li',3),('beryllium','Be',4),('boron','B',5),('carbon','C',6),('nitrogen','N',7),('oxygen','O',8),('fluorine','F',9),('neon','Ne',10),('sodium','Na',11),('magnesium','Mg',12),('aluminium','Al',13),('silicon','Si',14),('phosphorus','P',15),('sulfur','S',16),('chlorine','Cl',17),('argon','Ar',18),('potassium','K',19),('calcium','Ca',20),('scandium','Sc',21),('titanium','Ti',22)]
    for i,(n,s,z) in enumerate(elements,1): add(i,f'What is the atomic number of {n} ({s})?',[str(z-2),str(z),str(z+2),str(z+10)],str(z),'Atomic structure','Easy')
    for i,(n,s,z) in enumerate(elements,21): add(i,f'How many protons are present in one atom of {n} ({s})?',[str(z-1),str(z),str(z+1),str(z*2)],str(z),'Atomic structure','Easy')
    masses=[(0.25,24),(0.40,18),(0.75,12),(1.20,10),(1.50,8),(2.00,6),(2.50,4),(3.00,3),(0.60,20),(0.90,15)]
    for i,(m,mr) in enumerate(masses,41):
        ans=m*mr; add(i,f'How many grams are present in {m:g} mol of a substance with relative formula mass {mr}?',[f'{ans-1:g}',f'{ans:g}',f'{ans+1:g}',f'{ans*2:g}'],f'{ans:g}','Amount of substance')
    vols=[(0.20,0.050),(0.35,0.020),(0.60,0.025),(0.80,0.010),(1.20,0.005),(0.15,0.040),(0.45,0.030),(0.90,0.020),(1.50,0.004),(2.00,0.003)]
    for i,(c,v) in enumerate(vols,51):
        ans=c*v; add(i,f'What amount of solute is present in {v:g} dm3 of a {c:g} mol dm−3 solution?',[f'{ans/2:g}',f'{ans:g}',f'{ans*2:g}',f'{c+v:g}'],f'{ans:g}','Amount of substance')
    heat=[(1.0,5),(2.0,10),(1.5,8),(0.8,12),(2.5,6),(3.0,4),(1.2,15),(0.5,20),(4.0,3),(2.2,7)]
    for i,(m,d) in enumerate(heat,61):
        ans=m*4.18*d; add(i,f'{m:g} g of water is heated by {d} °C. Using c = 4.18 J g−1 K−1, what energy is transferred?',[f'{ans/2:.1f}',f'{ans:.1f}',f'{ans*2:.1f}',f'{ans+100:.1f}'],f'{ans:.1f}','Energetics')
    acids=[('HCl','Cl−'),('H2SO4','HSO4−'),('NH4+','NH3'),('H2CO3','HCO3−'),('H2O','OH−'),('H3O+','H2O'),('CH3COOH','CH3COO−'),('HNO3','NO3−'),('HSO4−','SO4^2−'),('HCO3−','CO3^2−')]
    for i,(acid,base) in enumerate(acids,71): add(i,f'Which species is the conjugate base of {acid}?',[base,'H+','OH−',acid],base,'Acids and bases','Easy')
    organic=[('ethane','C2H6','a single C–C bond'),('ethene','C2H4','a C=C double bond'),('ethyne','C2H2','a C≡C triple bond'),('propane','C3H8','single C–C bonds'),('propene','C3H6','one C=C bond'),('benzene','C6H6','a delocalised π system'),('methanol','CH3OH','an O–H bond'),('ethanol','C2H5OH','an O–H bond'),('ethanoic acid','CH3COOH','a carboxylic acid group'),('propanone','CH3COCH3','a ketone group')]
    for i,(n,f,feature) in enumerate(organic,81): add(i,f'Which statement correctly describes {n} ({f})',[feature,'It contains no covalent bonds','It is a metal','It contains only ionic bonds'],feature,'Organic chemistry')
    rates=[('increases','higher temperature'),('decreases','lower temperature'),('increases','a catalyst'),('increases','greater concentration of reactants'),('increases','greater surface area of a solid reactant'),('decreases','lower concentration of reactants'),('increases','higher gas pressure when gas reactants are involved'),('decreases','lower gas pressure when gas reactants are involved'),('increases','more frequent successful collisions'),('decreases','fewer successful collisions')]
    for i,(ans,cond) in enumerate(rates,91): add(i,f'What is the expected effect on reaction rate of {cond}?',[ans,'decreases' if ans=='increases' else 'increases','no change','the reaction becomes impossible'],ans,'Rates of reaction','Easy')
    return out
