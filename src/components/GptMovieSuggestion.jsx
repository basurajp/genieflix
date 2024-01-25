import React from "react";
import Loading from "react-loading";
import { useSelector } from "react-redux";
import MovieList from "./MovieList";

const GptMovieSuggestion = () => {
  const gpt = useSelector((store) => store.gpt);
  const { gptSearchedMovies, movieName } = gpt;
  if (!movieName) return <Loading />;
  return (
    <div className="px-0 py-2  mx  bg-black text-white bg-opacity-90">
      {movieName.map((eachMvie, index) => (
        <MovieList
          title={eachMvie}
          movies={gptSearchedMovies[index]}
          key={eachMvie}
        />
      ))}
    </div>
  ); 
};

export default GptMovieSuggestion;
