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
  Used in: [03](03_chunk_shapes.md), [11](11_ocsvm_anomaly.md)

- A. A. E. Ahmed and I. Traore, "A new biometric technology based on mouse dynamics," *IEEE Trans. Dependable Secure Comput.*, vol. 4, no. 3, pp. 165–179, Jul.–Sep. 2007, doi: [10.1109/TDSC.2007.70207](https://doi.org/10.1109/TDSC.2007.70207).  
  Used in: [03](03_chunk_shapes.md), [10](10_hull_anomaly.md), [11](11_ocsvm_anomaly.md)

- M. Antal and E. Egyed-Zsigmond, "Intrusion detection using mouse dynamics," *IET Biometrics*, vol. 8, no. 5, pp. 285–294, 2019, doi: [10.1049/iet-bmt.2018.5126](https://doi.org/10.1049/iet-bmt.2018.5126).  
  Used in: [03](03_chunk_shapes.md), [10](10_hull_anomaly.md)

- A. K. Jain, A. Ross, and S. Prabhakar, "An introduction to biometric recognition," *IEEE Trans. Circuits Syst. Video Technol.*, vol. 14, no. 1, pp. 4–20, Jan. 2004, doi: [10.1109/TCSVT.2003.818349](https://doi.org/10.1109/TCSVT.2003.818349).  
  Used in: [05](05_threshold.md), [10](10_hull_anomaly.md), [12](12_dtw_anomaly.md), [13](13_enroll_sweep.md)

## Stroke normalization and features

- J. O. Wobbrock, A. D. Wilson, and Y. Li, "Gestures without libraries, toolkits or training: A \$1 recognizer for user interface prototypes," in *Proc. 20th Annu. ACM Symp. User Interface Softw. Technol. (UIST)*, 2007, pp. 159–168, doi: [10.1145/1294211.1294238](https://doi.org/10.1145/1294211.1294238).  
  Used in: [03](03_chunk_shapes.md)

- G. E. P. Box and D. R. Cox, "An analysis of transformations," *J. Roy. Statist. Soc. Ser. B*, vol. 26, no. 2, pp. 211–243, 1964, doi: [10.1111/j.2517-6161.1964.tb00553.x](https://doi.org/10.1111/j.2517-6161.1964.tb00553.x).  
  Used in: [11](11_ocsvm_anomaly.md)

## Dynamic Time Warping

- H. Sakoe and S. Chiba, "Dynamic programming algorithm optimization for spoken word recognition," *IEEE Trans. Acoust., Speech, Signal Process.*, vol. 26, no. 1, pp. 43–49, Feb. 1978, doi: [10.1109/TASSP.1978.1163055](https://doi.org/10.1109/TASSP.1978.1163055).  
  Used in: [04](04_match_shapes.md), [12](12_dtw_anomaly.md), [14](14_plot_matches.md), [15](15_genuine_check.md)

- E. Keogh and C. A. Ratanamahatana, "Exact indexing of dynamic time warping," *Knowl. Inf. Syst.*, vol. 7, no. 3, pp. 358–386, Mar. 2005, doi: [10.1007/s10115-004-0154-9](https://doi.org/10.1007/s10115-004-0154-9).  
  Used in: [04](04_match_shapes.md), [12](12_dtw_anomaly.md), [14](14_plot_matches.md), [15](15_genuine_check.md)

- T. Rakthanmanon, B. Campana, A. Mueen, G. Batista, B. Westover, Q. Zhu, J. Zakaria, and E. Keogh, "Searching and mining trillions of time series subsequences under dynamic time warping," in *Proc. 18th ACM SIGKDD Int. Conf. Knowl. Discov. Data Min. (KDD)*, 2012, pp. 262–270, doi: [10.1145/2339530.2339576](https://doi.org/10.1145/2339530.2339576).  
  Used in: [04](04_match_shapes.md), [12](12_dtw_anomaly.md)

## Hulls and geometry

- R. L. Graham, "An efficient algorithm for determining the convex hull of a finite planar set," *Inf. Process. Lett.*, vol. 1, no. 4, pp. 132–133, Jun. 1972, doi: [10.1016/0020-0190(72)90045-2](https://doi.org/10.1016/0020-0190(72)90045-2).  
  Used in: [09](09_build_hulls.md)

- D. T. Lee and B. J. Schachter, "Two algorithms for constructing a Delaunay triangulation," *Int. J. Comput. Inf. Sci.*, vol. 9, no. 3, pp. 219–242, Jun. 1980, doi: [10.1007/BF00977785](https://doi.org/10.1007/BF00977785).  
  Used in: [09](09_build_hulls.md)

- M. Duckham, L. Kulik, M. Worboys, and A. Galton, "Efficient generation of simple polygons for characterizing the shape of a set of points in the plane," *Pattern Recognit.*, vol. 41, no. 10, pp. 3224–3236, Oct. 2008, doi: [10.1016/j.patcog.2008.03.023](https://doi.org/10.1016/j.patcog.2008.03.023).  
  Used in: [09](09_build_hulls.md)

- B. Braden, "The surveyor's area formula," *College Math. J.*, vol. 17, no. 4, pp. 326–337, Sep. 1986, doi: [10.1080/07468342.1986.11972974](https://doi.org/10.1080/07468342.1986.11972974).  
  Used in: [09](09_build_hulls.md)

- GEOS contributors, "geos::algorithm::ConvexHull class reference" ("Uses the Graham Scan algorithm"), GEOS documentation. [Online]. Available: https://libgeos.org/doxygen/classgeos_1_1algorithm_1_1ConvexHull.html  
  Used in: [09](09_build_hulls.md)

- GEOS contributors, "geos::algorithm::hull::ConcaveHull class reference," GEOS documentation. [Online]. Available: https://libgeos.org/doxygen/classgeos_1_1algorithm_1_1hull_1_1ConcaveHull.html  
  Used in: [09](09_build_hulls.md)

- Shapely contributors, "shapely.concave_hull," Shapely 2 documentation. [Online]. Available: https://shapely.readthedocs.io/en/stable/reference/shapely.concave_hull.html  
  Used in: [09](09_build_hulls.md)

- Shapely contributors, "shapely.contains_xy," Shapely 2 documentation. [Online]. Available: https://shapely.readthedocs.io/en/stable/reference/shapely.contains_xy.html  
  Used in: [10](10_hull_anomaly.md)

## One-Class SVM and scaling

- B. Schölkopf, J. C. Platt, J. Shawe-Taylor, A. J. Smola, and R. C. Williamson, "Estimating the support of a high-dimensional distribution," *Neural Comput.*, vol. 13, no. 7, pp. 1443–1471, Jul. 2001, doi: [10.1162/089976601750264965](https://doi.org/10.1162/089976601750264965).  
  Used in: [11](11_ocsvm_anomaly.md)

- F. Pedregosa *et al.*, "Scikit-learn: Machine learning in Python," *J. Mach. Learn. Res.*, vol. 12, pp. 2825–2830, 2011. [Online]. Available: https://jmlr.org/papers/v12/pedregosa11a.html  
  Used in: [11](11_ocsvm_anomaly.md)

- scikit-learn developers, "sklearn.svm.OneClassSVM," scikit-learn documentation. [Online]. Available: https://scikit-learn.org/stable/modules/generated/sklearn.svm.OneClassSVM.html  
  Used in: [11](11_ocsvm_anomaly.md)

- scikit-learn developers, "Support Vector Machines: Complexity," scikit-learn User Guide, §1.4. [Online]. Available: https://scikit-learn.org/stable/modules/svm.html  
  Used in: [11](11_ocsvm_anomaly.md)

- scikit-learn developers, "Novelty and outlier detection," scikit-learn User Guide. [Online]. Available: https://scikit-learn.org/stable/modules/outlier_detection.html  
  Used in: [11](11_ocsvm_anomaly.md)

- scikit-learn developers, "sklearn.preprocessing.RobustScaler," scikit-learn documentation. [Online]. Available: https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.RobustScaler.html  
  Used in: [11](11_ocsvm_anomaly.md)

## Randomness, hashing and software

- R. Durstenfeld, "Algorithm 235: Random permutation," *Commun. ACM*, vol. 7, no. 7, p. 420, Jul. 1964, doi: [10.1145/364520.364540](https://doi.org/10.1145/364520.364540).  
  Used in: [00](00_config.md), [02](02_sample_sessions.md), [06](06_sweep.md)

- Python Software Foundation, "random — Generate pseudo-random numbers," Python 3 documentation. [Online]. Available: https://docs.python.org/3/library/random.html  
  Used in: [00](00_config.md), [01](01_sample_users.md), [02](02_sample_sessions.md), [06](06_sweep.md), [13](13_enroll_sweep.md)

- National Institute of Standards and Technology, "Secure Hash Standard (SHS)," FIPS PUB 180-4, Aug. 2015, doi: [10.6028/NIST.FIPS.180-4](https://doi.org/10.6028/NIST.FIPS.180-4).  
  Used in: [00](00_config.md)

- Python Software Foundation, "hashlib — Secure hashes and message digests," Python 3 documentation. [Online]. Available: https://docs.python.org/3/library/hashlib.html  
  Used in: [00](00_config.md)

- pandas developers, "pandas.DataFrame.sort_values" (the `kind` parameter: only "stable" keeps tied rows in order), pandas documentation. [Online]. Available: https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.sort_values.html  
  Used in: [00](00_config.md)

- NumPy developers, "numpy.interp," NumPy documentation. [Online]. Available: https://numpy.org/doc/stable/reference/generated/numpy.interp.html  
  Used in: [03](03_chunk_shapes.md)

- NumPy developers, "numpy.convolve," NumPy documentation. [Online]. Available: https://numpy.org/doc/stable/reference/generated/numpy.convolve.html  
  Used in: [10](10_hull_anomaly.md)

- S. K. Lam, A. Pitrou, and S. Seibert, "Numba: A LLVM-based Python JIT compiler," in *Proc. 2nd Workshop LLVM Compiler Infrastructure HPC*, 2015, pp. 1–6, doi: [10.1145/2833157.2833162](https://doi.org/10.1145/2833157.2833162).  
  Used in: [04](04_match_shapes.md), [14](14_plot_matches.md)

- Numba developers, "Automatic parallelization with @jit (prange)," Numba documentation. [Online]. Available: https://numba.readthedocs.io/en/stable/user/parallel.html  
  Used in: [04](04_match_shapes.md)

- Python Software Foundation, "multiprocessing — Process-based parallelism," Python 3 documentation. [Online]. Available: https://docs.python.org/3/library/multiprocessing.html  
  Used in: [07](07_plot_shapes.md)

- Jupyter developers, "Executing notebooks," nbconvert documentation. [Online]. Available: https://nbconvert.readthedocs.io/en/latest/execute_api.html  
  Used in: [08](08_run_notebook.md)
