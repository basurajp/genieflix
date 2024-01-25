import React from "react";
import MovieList from "./MovieList";
import { useSelector } from "react-redux";

const SecondaryContainer = () => {
  const movies = useSelector((store) => store.movies);

  return (
    <div className="bg-black md:mt-16  lg:h-[120vw]">
      <div className=" mt-0 md:-mt-52 pl-4 md:pl-12 relative z-20">
        <MovieList title={"Now Playing"} movies={movies.nowPlayingMovies} />

        <MovieList title={"Popular"} movies={movies.popularMovies} />
        <MovieList title={"Top rated Movies "} movies={movies.topratedMovies} />
        <MovieList title={"Upcoming"} movies={movies.upComingMvies} />
      </div>
    </div>
  );
};

export default SecondaryContainer;
