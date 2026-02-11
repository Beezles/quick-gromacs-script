#!/usr/bin/env python3
import subprocess
import os

def write_mdp_files(temp=298, ns_length=50):
    """Generates all required .mdp files with dynamic parameters."""
    
    #Calculate nsteps based on ns_length (assuming 1fs dt)
    #50ns = 50,000,000 steps [cite: 2, 3]
    total_steps = int(ns_length * 1000000)

    mdp_content = {
        "ions.mdp": "integrator = steep\n", #Created manually to avoid glitches 
        
        "minim.mdp": (
            "integrator  = steep\n"
            "emtol       = 1000.0\n"
            "emstep      = 0.01\n"
            "nsteps      = 50000\n"
            "nstlist     = 1\n"
            "cutoff-scheme = Verlet\n"
            "ns_type     = grid\n"
            "coulombtype = PME\n"
            "rcoulomb    = 1.0\n"
            "rvdw        = 1.0\n"
            "pbc         = xyz\n"
        ),

        "nvt.mdp": (
            f"define                  = -DPOSRES\n" #Restrain protein 
            "integrator              = md\n"
            "dt                      = 0.001\n" #1 fs
            "nsteps                  = 50000\n" #50 ps
            "nstxout                 = 500\n"
            "tcoupl                  = v-rescale\n"
            "tc-grps                 = Protein Non-Protein\n"
            "tau_t                   = 0.1     0.1\n"
            f"ref_t                   = {temp}     {temp}\n" #Variable temp
            "pcoupl                  = no\n"
            "pbc                     = xyz\n"
        ),

        "npt.mdp": (
            "define                  = -DPOSRES\n" 
            "integrator              = md\n"
            "dt                      = 0.001\n"
            "nsteps                  = 50000\n"
            "nstxout                 = 500\n"
            "tcoupl                  = v-rescale\n" 
            "tc-grps                 = Protein Non-Protein\n"
            "tau_t                   = 0.1     0.1\n"
            f"ref_t                   = {temp}     {temp}\n"
            "pcoupl                  = c-rescale\n"
            "pcoupltype              = isotropic\n"
            "tau_p                   = 2.0\n"
            "compressibility         = 4.5e-5\n"
            "ref_p                   = 1.0\n"
            "refcoord_scaling        = com\n"
            "coulombtype             = PME\n"
            "rcoulomb                = 1.0\n"
            f"fourierspacing          = 0.12\n" 
            "pme_order               = 4\n"
            "constraints             = h-bonds\n"
        ),

        "md.mdp": (
            "integrator              = md\n" 
            "dt                      = 0.001\n" #1 fs
            f"nsteps                  = {total_steps}\n" #50 ns
            "nstxout-compressed      = 5000\n" #Every 5 ps
            "tcoupl                  = v-rescale\n"
            "tc-grps                 = Protein Non-Protein\n"
            "tau_t                   = 0.1     0.1\n"
            f"ref_t                   = {temp}     {temp}\n"
            "pcoupl                  = c-rescale\n" 
            "pcoupltype              = isotropic\n"
            "tau_p                   = 2.0\n"
            "ref_p                   = 1.0\n"
            "compressibility         = 4.5e-5\n" 
            "coulombtype             = PME\n"
            "rcoulomb                = 1.0\n"
            "fourierspacing          = 0.12\n"
            "pme_order               = 4\n"
            "vdw-type                = Cut-off\n"
            "rvdw                    = 1.0\n" 
            "compressed-x-grps       = Protein\n" #Only save protein to .xtc
        )
    }

    for filename, content in mdp_content.items():
        with open(filename, "w") as f:
            f.write(content)
    print("Successfully generated all .mdp files.")

def run_step(command, input_val=None):
    """Helper to run shell commands with automated input."""
    try:
        subprocess.run(
            command, 
            shell=True, 
            check=True, 
            text=True, 
            input=input_val
        )
    except subprocess.CalledProcessError as e:
        print(f"Error during execution: {e}")
        exit(1)

# --- Workflow Starts Here ---
user_temp = input("Enter simulation temperature (default 298): ") or 298
user_ns = input("Enter simulation length in ns (default 50): ") or 50

#Step 0: Create Files
write_mdp_files(temp=user_temp, ns_length=float(user_ns))

#Step 1: Topology
pdb_name = input("PDB file name (without .pdb): ").strip()
#Use '8' for CHARMM27
run_step(f"gmx_mpi pdb2gmx -f {pdb_name}.pdb -o protein_processed.gro -water tips3p -ignh", input_val="8")

#Step 2: Box & Solvate
run_step("gmx_mpi editconf -f protein_processed.gro -o box.gro -c -d 1.0 -bt cubic")
run_step("gmx_mpi solvate -cp box.gro -cs spc216.gro -o solvated.gro -p topol.top")

#Step 3: Ions
run_step("gmx_mpi grompp -f ions.mdp -c solvated.gro -p topol.top -o ions.tpr")
#Select group 13 (SOL) automatically 
run_step("gmx_mpi genion -s ions.tpr -o ions.gro -p topol.top -pname NA -nname CL -neutral", input_val="13")

#Step 4: EM & Equilibrations
run_step("gmx_mpi grompp -f minim.mdp -c ions.gro -p topol.top -o em.tpr")
run_step("gmx_mpi mdrun -v -deffnm em")

run_step("gmx_mpi grompp -f nvt.mdp -c em.gro -r em.gro -p topol.top -o nvt.tpr") # [cite: 23]
run_step("gmx_mpi mdrun -v -deffnm nvt")

run_step("gmx_mpi grompp -f npt.mdp -c nvt.gro -r nvt.gro -t nvt.cpt -p topol.top -o npt.tpr")
run_step("gmx_mpi mdrun -v -deffnm npt")

#Step 5: Production
run_step(f"gmx_mpi grompp -f md.mdp -c npt.gro -t npt.cpt -p topol.top -o md_{user_ns}ns.tpr")
run_step(f"gmx_mpi mdrun -v -deffnm md_{user_ns}ns")


print(f"\nSimulation complete for {user_ns}ns at {user_temp}K!")

