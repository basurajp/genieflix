import { render, screen } from "@testing-library/react"
import MovieList from "../MovieList"

test('movie card is testing ', ()=>{
    render(<MovieList />)
    
   // asserstion 
   const heading =  screen.getByRole('heading')
   expect(heading).toBeInTheDocument()

})