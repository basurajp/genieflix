import React from "react";
import { BG_URL } from "../utils/constant";
import GptSearchBar from "./GptSearchBar";
import GptMovieSuggestion from "./GptMovieSuggestion";

const GptSearch = () => {
  return (
    <div className="">
      <div className="fixed -z-10 ">
        <img className="h-[100vh] lg:h-auto object-cover" src={BG_URL} alt="" />
      </div>
      <GptSearchBar />
      <GptMovieSuggestion />
    </div>
  );
};

export default GptSearch;
