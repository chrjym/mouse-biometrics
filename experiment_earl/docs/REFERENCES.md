# References for the script documentation

Every source cited in the per-script pages, in IEEE style and grouped by topic. Each DOI was checked against
Crossref on 2026-10-14. Documentation links were opened the same day; the readthedocs pages (Shapely, Numba, nbconvert)
rate-limited the automated check, so open them once by hand. "Used in" lists the pages that cite it.
Pages number their references locally, in the order they first cite them.

Papers are the sources to cite in the thesis. Documentation links describe the exact software behaviour we rely on,
for reproducibility; they are not academic citations. Before citing any of these in a chapter, add it to
`paper/references/`, as `CLAUDE.md` requires.

[← index](README.md)

## Dataset

- Á. Fülöp, L. Kovács, T. Kurics, and E. Windhager-Pokol, "Balabit Mouse Dynamics Challenge data set," 2016. [Online]. Available: https://github.com/balabit/Mouse-Dynamics-Challenge  
  Used in: [00](00_config.md), [01](01_sample_users.md)

## Mouse dynamics and biometric evaluation

- H. Gamboa and A. Fred, "A behavioral biometric system based on human-computer interaction," in *Proc. SPIE 5404, Biometric Technology for Human Identification*, 2004, pp. 381–392, doi: [10.1117/12.542625](https://doi.org/10.1117/12.542625).  
  Used in: [03](03_chunk_shapes.md)

- A. A. E. Ahmed and I. Traore, "A new biometric technology based on mouse dynamics," *IEEE Trans. Dependable Secure Comput.*, vol. 4, no. 3, pp. 165–179, Jul.–Sep. 2007, doi: [10.1109/TDSC.2007.70207](https://doi.org/10.1109/TDSC.2007.70207).  
  Used in: [03](03_chunk_shapes.md)

- M. Antal and E. Egyed-Zsigmond, "Intrusion detection using mouse dynamics," *IET Biometrics*, vol. 8, no. 5, pp. 285–294, 2019, doi: [10.1049/iet-bmt.2018.5126](https://doi.org/10.1049/iet-bmt.2018.5126).  
  Used in: [03](03_chunk_shapes.md)

- A. K. Jain, A. Ross, and S. Prabhakar, "An introduction to biometric recognition," *IEEE Trans. Circuits Syst. Video Technol.*, vol. 14, no. 1, pp. 4–20, Jan. 2004, doi: [10.1109/TCSVT.2003.818349](https://doi.org/10.1109/TCSVT.2003.818349).  
  Used in: [05](05_sensitivity.md)

## Stroke normalization and features

- J. O. Wobbrock, A. D. Wilson, and Y. Li, "Gestures without libraries, toolkits or training: A \$1 recognizer for user interface prototypes," in *Proc. 20th Annu. ACM Symp. User Interface Softw. Technol. (UIST)*, 2007, pp. 159–168, doi: [10.1145/1294211.1294238](https://doi.org/10.1145/1294211.1294238).  
  Used in: [03](03_chunk_shapes.md)

## Dynamic Time Warping

- H. Sakoe and S. Chiba, "Dynamic programming algorithm optimization for spoken word recognition," *IEEE Trans. Acoust., Speech, Signal Process.*, vol. 26, no. 1, pp. 43–49, Feb. 1978, doi: [10.1109/TASSP.1978.1163055](https://doi.org/10.1109/TASSP.1978.1163055).  
  Used in: [04](04_match_shapes.md), [08](08_plot_matches.md), [09](09_genuine_check.md)

- E. Keogh and C. A. Ratanamahatana, "Exact indexing of dynamic time warping," *Knowl. Inf. Syst.*, vol. 7, no. 3, pp. 358–386, Mar. 2005, doi: [10.1007/s10115-004-0154-9](https://doi.org/10.1007/s10115-004-0154-9).  
  Used in: [04](04_match_shapes.md), [08](08_plot_matches.md), [09](09_genuine_check.md)

- T. Rakthanmanon, B. Campana, A. Mueen, G. Batista, B. Westover, Q. Zhu, J. Zakaria, and E. Keogh, "Searching and mining trillions of time series subsequences under dynamic time warping," in *Proc. 18th ACM SIGKDD Int. Conf. Knowl. Discov. Data Min. (KDD)*, 2012, pp. 262–270, doi: [10.1145/2339530.2339576](https://doi.org/10.1145/2339530.2339576).  
  Used in: [04](04_match_shapes.md)

## Randomness, hashing and software

- R. Durstenfeld, "Algorithm 235: Random permutation," *Commun. ACM*, vol. 7, no. 7, p. 420, Jul. 1964, doi: [10.1145/364520.364540](https://doi.org/10.1145/364520.364540).  
  Used in: [00](00_config.md), [02](02_sample_sessions.md)

- Python Software Foundation, "random — Generate pseudo-random numbers," Python 3 documentation. [Online]. Available: https://docs.python.org/3/library/random.html  
  Used in: [00](00_config.md), [01](01_sample_users.md), [02](02_sample_sessions.md)

- National Institute of Standards and Technology, "Secure Hash Standard (SHS)," FIPS PUB 180-4, Aug. 2015, doi: [10.6028/NIST.FIPS.180-4](https://doi.org/10.6028/NIST.FIPS.180-4).  
  Used in: [00](00_config.md)

- Python Software Foundation, "hashlib — Secure hashes and message digests," Python 3 documentation. [Online]. Available: https://docs.python.org/3/library/hashlib.html  
  Used in: [00](00_config.md)

- pandas developers, "pandas.DataFrame.sort_values" (the `kind` parameter: only "stable" keeps tied rows in order), pandas documentation. [Online]. Available: https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.sort_values.html  
  Used in: [00](00_config.md)

- NumPy developers, "numpy.interp," NumPy documentation. [Online]. Available: https://numpy.org/doc/stable/reference/generated/numpy.interp.html  
  Used in: [03](03_chunk_shapes.md)

- S. K. Lam, A. Pitrou, and S. Seibert, "Numba: A LLVM-based Python JIT compiler," in *Proc. 2nd Workshop LLVM Compiler Infrastructure HPC*, 2015, pp. 1–6, doi: [10.1145/2833157.2833162](https://doi.org/10.1145/2833157.2833162).  
  Used in: [04](04_match_shapes.md), [08](08_plot_matches.md)

- Numba developers, "Automatic parallelization with @jit (prange)," Numba documentation. [Online]. Available: https://numba.readthedocs.io/en/stable/user/parallel.html  
  Used in: [04](04_match_shapes.md)

- Python Software Foundation, "multiprocessing — Process-based parallelism," Python 3 documentation. [Online]. Available: https://docs.python.org/3/library/multiprocessing.html  
  Used in: [06](06_plot_shapes.md)

- Jupyter developers, "Executing notebooks," nbconvert documentation. [Online]. Available: https://nbconvert.readthedocs.io/en/latest/execute_api.html  
  Used in: [07](07_run_notebook.md)
