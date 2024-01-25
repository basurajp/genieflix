import React, { useEffect } from "react";
import lang from "../utils/languageConstant";
import { useDispatch, useSelector } from "react-redux";
import { API_OPTION } from "../utils/constant";
import { addGptMovieResult } from "../rtk/gptSlice";

const GptSearchBar = () => {
  const langDetails = useSelector((store) => store.config.lang);
  const dispatch = useDispatch();

  const retroMovie = [
    "Sholay",
    "Mughal-e-Azam",
    "Pakeezah",
    "Amar Akbar Anthony",
    "Guide",
  ];

  // search movie in tmdb

  const handleFetchMovie = async (movie) => {
    const data = await fetch(
      `https://api.themoviedb.org/3/search/movie?query=${movie}&include_adult=false&language=en-US&page=1`,
      API_OPTION
    );
    const json = await data.json();
    return json.results;
  };

  const handleMultiplePromises = async () => {
    const movieData = retroMovie.map((moviName, index) =>
      handleFetchMovie(moviName)
    ); // return promise array

    const tmdbResult = await Promise.all(movieData);
    dispatch(
      addGptMovieResult({
        movieName: retroMovie,
        gptSearchedMovies: tmdbResult,
      })
    );
  };

  useEffect(() => {
    handleMultiplePromises();
  }, []);

  return (
    <div className="pt-[30%] lg:pt-[15%] lg:flex lg:items-center lg:justify-center">
      <form
        className="bg-black lg:w-[60%]  "
        onSubmit={(e) => e.preventDefault()}
      >
        <input
          value={"Restro movies "}
          disabled
          type="text"
          className="py-2 px-4 w-[80%]  lg:w-[85%] m-2 rounded-lg bg-white"
          placeholder={lang[langDetails].gptSearchPlaceholder}
        />
        <button
          onClick={handleFetchMovie}
          className="py-2 px-2 bg-red-500 text-white rounded-lg"
        >
          {lang[langDetails].search}
        </button>
      </form>
    </div>
  );
};

export default GptSearchBar;
