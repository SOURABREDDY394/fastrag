function PageHeader() {
  return (
    <header className="mb-7 flex items-start gap-5">
      <div className="mt-1 h-20 w-1.5 rounded-full bg-teal-600" />
      <div>
        <h1 className="text-4xl font-bold tracking-normal text-slate-950 sm:text-5xl">
          StudyRAG
        </h1>
        <p className="mt-3 max-w-2xl text-base leading-7 text-slate-600">
          Upload study materials and get accurate answers with page references.
        </p>
      </div>
    </header>
  );
}

export default PageHeader;
